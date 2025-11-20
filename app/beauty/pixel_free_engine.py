import ctypes
import ctypes.util
import logging
import os
import queue
import threading
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import cv2
from OpenGL import GL
try:
    import glfw  # type: ignore
except Exception:  # pylint: disable=broad-except
    glfw = None

LOGGER = logging.getLogger(__name__)
_GL_READY = False


def _ensure_gl_functions_loaded():
    global _GL_READY  # pylint: disable=global-statement
    if _GL_READY or os.name != "nt":
        return
    opengl32_path = ctypes.util.find_library("opengl32")
    if not opengl32_path:
        raise PixelFreeError("无法找到 opengl32.dll，无法初始化 PixelFree。")
    opengl32 = ctypes.WinDLL(opengl32_path)
    kernel32 = ctypes.WinDLL("kernel32.dll")
    get_proc = kernel32.GetProcAddress
    get_proc.restype = ctypes.c_void_p
    get_proc.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

    gl_get_string = get_proc(opengl32._handle, b"glGetString")  # type: ignore[attr-defined]
    if not gl_get_string:
        raise PixelFreeError("加载 glGetString 失败，OpenGL 环境不可用。")

    wgl_get_proc = opengl32.wglGetProcAddress
    wgl_get_proc.restype = ctypes.c_void_p
    wgl_get_proc.argtypes = [ctypes.c_char_p]

    required_funcs = [
        "glCreateProgram", "glCreateShader", "glShaderSource", "glCompileShader",
        "glAttachShader", "glLinkProgram", "glUseProgram", "glGenTextures",
        "glBindTexture", "glTexImage2D", "glTexParameteri", "glDrawArrays",
    ]
    for func in required_funcs:
        ptr = wgl_get_proc(func.encode())
        if ptr is None:
            LOGGER.warning("无法通过 wglGetProcAddress 预加载 %s", func)
    _GL_READY = True


class PixelFreeError(RuntimeError):
    """Raised when PixelFree SDK operations fail."""


class PFDetectFormat(IntEnum):
    PFFORMAT_UNKNOWN = 0
    PFFORMAT_IMAGE_RGB = 1
    PFFORMAT_IMAGE_BGR = 2
    PFFORMAT_IMAGE_RGBA = 3
    PFFORMAT_IMAGE_BGRA = 4
    PFFORMAT_IMAGE_ARGB = 5
    PFFORMAT_IMAGE_ABGR = 6
    PFFORMAT_IMAGE_GRAY = 7
    PFFORMAT_IMAGE_YUV_NV12 = 8
    PFFORMAT_IMAGE_YUV_NV21 = 9
    PFFORMAT_IMAGE_YUV_I420 = 10
    PFFORMAT_IMAGE_TEXTURE = 11


class PFRotationMode(IntEnum):
    PFRotationMode0 = 0
    PFRotationMode90 = 1
    PFRotationMode180 = 2
    PFRotationMode270 = 3


class PFSrcType(IntEnum):
    PFSrcTypeFilter = 0
    PFSrcTypeAuthFile = 2
    PFSrcTypeStickerFile = 3


class PFBeautyFiterType(IntEnum):
    PFBeautyFiterTypeFace_EyeStrength = 0
    PFBeautyFiterTypeFace_thinning = 1
    PFBeautyFiterTypeFace_narrow = 2
    PFBeautyFiterTypeFace_chin = 3
    PFBeautyFiterTypeFace_V = 4
    PFBeautyFiterTypeFace_small = 5
    PFBeautyFiterTypeFace_nose = 6
    PFBeautyFiterTypeFace_forehead = 7
    PFBeautyFiterTypeFace_mouth = 8
    PFBeautyFiterTypeFace_philtrum = 9
    PFBeautyFiterTypeFace_long_nose = 10
    PFBeautyFiterTypeFace_eye_space = 11
    PFBeautyFiterTypeFace_smile = 12
    PFBeautyFiterTypeFace_eye_rotate = 13
    PFBeautyFiterTypeFace_canthus = 14
    PFBeautyFiterTypeFaceBlurStrength = 15
    PFBeautyFiterTypeFaceWhitenStrength = 16
    PFBeautyFiterTypeFaceRuddyStrength = 17
    PFBeautyFiterTypeFaceSharpenStrength = 18
    PFBeautyFiterTypeFaceM_newWhitenStrength = 19
    PFBeautyFiterTypeFaceH_qualityStrength = 20
    PFBeautyFiterTypeFaceEyeBrighten = 21
    PFBeautyFiterName = 22
    PFBeautyFiterStrength = 23
    PFBeautyFiterLvmu = 24
    PFBeautyFiterSticker2DFilter = 25
    PFBeautyFiterTypeOneKey = 26
    PFBeautyFiterWatermark = 27
    PFBeautyFiterExtend = 28
    PFBeautyFilterNasolabial = 29
    PFBeautyFilterBlackEye = 30


class PFIamgeInput(ctypes.Structure):
    _fields_ = [
        ("textureID", ctypes.c_uint),
        ("wigth", ctypes.c_int),
        ("height", ctypes.c_int),
        ("p_data0", ctypes.c_void_p),
        ("p_data1", ctypes.c_void_p),
        ("p_data2", ctypes.c_void_p),
        ("stride_0", ctypes.c_int),
        ("stride_1", ctypes.c_int),
        ("stride_2", ctypes.c_int),
        ("format", ctypes.c_int),
        ("rotationMode", ctypes.c_int),
    ]


@dataclass
class PixelFreeConfig:
    dll_path: Union[str, Path]
    auth_path: Union[str, Path]
    filter_path: Optional[Union[str, Path]] = None

    def as_posix(self) -> "PixelFreeConfig":
        return PixelFreeConfig(
            dll_path=str(Path(self.dll_path)),
            auth_path=str(Path(self.auth_path)),
            filter_path=str(Path(self.filter_path)) if self.filter_path else None,
        )


class PixelFreeEngine:
    """Thin ctypes wrapper around PixelFreeEffects SDK DLL."""

    def __init__(self, config: PixelFreeConfig):
        self._config = config.as_posix()
        self._dll: Optional[ctypes.CDLL] = None
        self._handle: Optional[ctypes.c_void_p] = None
        self._param_cache: Dict[int, Union[float, str, bool]] = {}
        self._data_buffer = None
        self._lock = threading.Lock()
        if os.name != "nt":
            raise PixelFreeError("PixelFree SDK 目前仅支持 Windows 平台 (需 OpenGL 环境)")
        self._load()

    # ------------------------------------------------------------------ #
    # Initialisation helpers
    # ------------------------------------------------------------------ #
    def _load(self):
        self._release()
        dll_path = Path(self._config.dll_path)
        auth_path = Path(self._config.auth_path)
        if not dll_path.is_file():
            raise PixelFreeError(f"未找到 PixelFree DLL: {dll_path}")
        if not auth_path.is_file():
            raise PixelFreeError(f"未找到 PixelFree 授权文件: {auth_path}")

        try:
            self._dll = ctypes.CDLL(str(dll_path))
        except OSError as exc:
            raise PixelFreeError(f"加载 PixelFree DLL 失败: {exc}") from exc

        self._setup_function_prototypes()
        self._handle = self._dll.PF_NewPixelFree()
        if not self._handle:
            raise PixelFreeError("创建 PixelFree 实例失败 (PF_NewPixelFree 返回 NULL)")

        self._load_bundle(auth_path, PFSrcType.PFSrcTypeAuthFile)
        if self._config.filter_path:
            filter_path = Path(self._config.filter_path)
            if not filter_path.is_file():
                raise PixelFreeError(f"未找到滤镜 bundle: {filter_path}")
            self._load_bundle(filter_path, PFSrcType.PFSrcTypeFilter)
        LOGGER.info("PixelFree SDK 加载完成")

    def reload(self, config: PixelFreeConfig):
        """Reload SDK resources with a new configuration."""
        self._config = config.as_posix()
        self._param_cache.clear()
        self._load()

    def close(self):
        """Dispose SDK resources."""
        self._release()

    def _release(self):
        if self._dll and self._handle:
            destroy = getattr(self._dll, "PF_DeletePixelFree", None)
            if destroy:
                try:
                    destroy(self._handle)
                except Exception as exc:  # pylint: disable=broad-except
                    LOGGER.warning("释放 PixelFree 句柄失败: %s", exc)
        self._handle = None
        self._dll = None

    def __del__(self):
        try:
            self.close()
        except Exception:  # pylint: disable=broad-except
            pass

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def process_bgr_frame(
        self,
        frame: np.ndarray,
        rotation_mode: PFRotationMode = PFRotationMode.PFRotationMode0,
    ) -> np.ndarray:
        if not self._handle or not self._dll:
            raise PixelFreeError("PixelFree 尚未初始化")
        if frame is None:
            raise PixelFreeError("输入帧为空")

        frame = np.require(frame, dtype=np.uint8, requirements=["C"])
        if frame.ndim != 3:
            raise PixelFreeError("仅支持 HxWxC 格式图像")
        height, width, channels = frame.shape
        if channels not in (3, 4):
            raise PixelFreeError("仅支持 BGR/BGRA 图像")

        img_input = PFIamgeInput()
        img_input.textureID = 0
        img_input.wigth = width
        img_input.height = height
        img_input.p_data0 = ctypes.c_void_p(frame.ctypes.data)
        img_input.p_data1 = None
        img_input.p_data2 = None
        img_input.stride_0 = frame.strides[0]
        img_input.stride_1 = 0
        img_input.stride_2 = 0
        img_input.format = (
            PFDetectFormat.PFFORMAT_IMAGE_BGRA
            if channels == 4
            else PFDetectFormat.PFFORMAT_IMAGE_BGR
        )
        img_input.rotationMode = int(rotation_mode)

        with self._lock:
            self._data_buffer = img_input.p_data0  # keep reference alive
            result = self._dll.PF_processWithBuffer(  # type: ignore[attr-defined]
                self._handle,
                ctypes.pointer(img_input),
            )
        if result <= 0:
            raise PixelFreeError(f"PF_processWithBuffer 失败, 返回值: {result}")
        return frame

    def process_texture(
        self,
        texture_id: int,
        width: int,
        height: int,
        rotation_mode: PFRotationMode = PFRotationMode.PFRotationMode0,
    ) -> int:
        if not self._handle or not self._dll:
            raise PixelFreeError("PixelFree 尚未初始化")
        if texture_id <= 0:
            raise PixelFreeError("无效的纹理 ID")

        img_input = PFIamgeInput()
        img_input.textureID = texture_id
        img_input.wigth = width
        img_input.height = height
        img_input.p_data0 = None
        img_input.p_data1 = None
        img_input.p_data2 = None
        img_input.stride_0 = 0
        img_input.stride_1 = 0
        img_input.stride_2 = 0
        img_input.format = PFDetectFormat.PFFORMAT_IMAGE_TEXTURE
        img_input.rotationMode = int(rotation_mode)

        with self._lock:
            result = self._dll.PF_processWithBuffer(  # type: ignore[attr-defined]
                self._handle,
                ctypes.pointer(img_input),
            )
        if result <= 0:
            raise PixelFreeError(f"PF_processWithBuffer 失败, 返回值: {result}")
        return result

    def apply_beauty_parameters(self, params: Dict[PFBeautyFiterType, Union[float, str, bool]]):
        if not params:
            return
        with self._lock:
            for pf_type, value in params.items():
                if pf_type == PFBeautyFiterType.PFBeautyFiterTypeOneKey:
                    continue
                if value is None:
                    continue
                cached = self._param_cache.get(pf_type.value)
                if cached == value:
                    continue
                self._set_parameter_locked(pf_type, value)
                self._param_cache[pf_type.value] = value

    @staticmethod
    def rotation_from_degrees(degrees: Union[int, str]) -> PFRotationMode:
        try:
            deg = int(degrees)
        except (TypeError, ValueError):
            deg = 0
        deg = deg % 360
        mapping = {
            0: PFRotationMode.PFRotationMode0,
            90: PFRotationMode.PFRotationMode90,
            180: PFRotationMode.PFRotationMode180,
            270: PFRotationMode.PFRotationMode270,
        }
        return mapping.get(deg, PFRotationMode.PFRotationMode0)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _setup_function_prototypes(self):
        assert self._dll is not None
        self._dll.PF_NewPixelFree.restype = ctypes.c_void_p
        self._dll.PF_processWithBuffer.restype = ctypes.c_int
        self._dll.PF_processWithBuffer.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(PFIamgeInput),
        ]
        self._dll.PF_createBeautyItemFormBundle.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
        ]
        set_param = getattr(self._dll, "PF_pixelFreeSetBeautyFilterParam", None)
        if set_param is None:
            set_param = getattr(self._dll, "PF_pixelFreeSetBeautyFiterParam")
        self._set_param_func = set_param
        self._set_param_func.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ]

    def _load_bundle(self, file_path: Path, bundle_type: PFSrcType):
        assert self._dll is not None and self._handle is not None
        try:
            data = file_path.read_bytes()
        except OSError as exc:
            raise PixelFreeError(f"读取资源失败: {file_path}") from exc
        buffer = ctypes.create_string_buffer(data)
        result = self._dll.PF_createBeautyItemFormBundle(  # type: ignore[attr-defined]
            self._handle,
            buffer,
            len(data),
            bundle_type.value,
        )
        if result != 0:
            LOGGER.debug("PF_createBeautyItemFormBundle 返回 %s", result)

    def _set_parameter_locked(self, param_type: PFBeautyFiterType, value: Union[float, str, bool]):
        assert self._dll is not None and self._handle is not None
        if isinstance(value, str):
            encoded = value.encode("utf-8")
            arg = ctypes.c_char_p(encoded)
        elif isinstance(value, bool):
            arg = ctypes.byref(ctypes.c_bool(value))
        else:
            clamped = max(0.0, min(float(value), 1.0))
            arg = ctypes.byref(ctypes.c_float(clamped))
        result = self._set_param_func(  # type: ignore[attr-defined]
            self._handle,
            param_type.value,
            arg,
        )
        if result not in (None, 0):
            LOGGER.debug("PF_pixelFreeSetBeautyFilterParam 返回 %s", result)


def build_default_config(base_dir: Optional[Union[str, Path]] = None) -> PixelFreeConfig:
    """Helper to build a config pointing to dependencies/pixel_free/* resources."""
    base = Path(base_dir or Path("dependencies") / "pixel_free")
    return PixelFreeConfig(
        dll_path=base / "PixelFree.dll",
        auth_path=base / "pixelfreeAuth.lic",
        filter_path=base / "filter_model.bundle",
    )


class PixelFreeWorker:
    """Runs PixelFreeEngine inside a dedicated thread to avoid threading issues."""

    def __init__(self, config: PixelFreeConfig):
        if glfw is None:
            raise PixelFreeError("未安装 glfw，无法创建 PixelFree 所需的 OpenGL 上下文。请先 `pip install glfw`。")
        self._config = config.as_posix()
        self._jobs: "queue.Queue[dict]" = queue.Queue()
        self._ready = threading.Event()
        self._startup_error: Optional[Exception] = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._ready.wait()
        if self._startup_error:
            raise self._startup_error

    def reload(self, config: PixelFreeConfig):
        return self._submit_job("reload", config=config.as_posix())

    def close(self):
        self._jobs.put({"type": "stop"})
        self._thread.join(timeout=2.0)

    def process(self, frame: np.ndarray, params: Dict[PFBeautyFiterType, Union[float, str, bool]], rotation_degrees: Union[int, str]):
        job = self._submit_job("process", frame=frame, params=params, rotation=rotation_degrees)
        return job

    def _submit_job(self, job_type: str, **kwargs):
        event = threading.Event()
        job = {"type": job_type, "event": event}
        job.update(kwargs)
        self._jobs.put(job)
        event.wait()
        error = job.get("error")
        if error:
            raise error
        return job.get("result")

    def _loop(self):
        if glfw is None:
            self._startup_error = PixelFreeError("未安装 glfw，无法初始化 PixelFree。")
            self._ready.set()
            return
        engine: Optional[PixelFreeEngine] = None
        context: Optional[_OffscreenGLContext] = None
        texture_helper: Optional[_GLTextureProcessor] = None
        try:
            context = _OffscreenGLContext()
            context.make_current()
            _ensure_gl_functions_loaded()
            texture_helper = _GLTextureProcessor()
            engine = PixelFreeEngine(self._config)
        except Exception as exc:  # pylint: disable=broad-except
            self._startup_error = exc
            self._ready.set()
            return
        self._ready.set()
        while True:
            job = self._jobs.get()
            job_type = job["type"]
            if job_type == "stop":
                break
            if job_type == "reload":
                try:
                    new_config: PixelFreeConfig = job["config"]
                    if engine:
                        engine.close()
                    if context:
                        context.make_current()
                        _ensure_gl_functions_loaded()
                    engine = PixelFreeEngine(new_config)
                    self._config = new_config
                except Exception as exc:  # pylint: disable=broad-except
                    job["error"] = exc
                finally:
                    job["event"].set()
                continue
            if job_type == "process":
                try:
                    if context:
                        context.make_current()
                    if not texture_helper:
                        raise PixelFreeError("OpenGL 纹理处理器未初始化")
                    params = job["params"]
                    rotation = job["rotation"]
                    tex_id, width, height = texture_helper.upload_frame(job["frame"])
                    output_frame = job["frame"]
                    try:
                        engine.apply_beauty_parameters(params)
                        rotation_mode = engine.rotation_from_degrees(rotation)
                        output_tex = engine.process_texture(tex_id, width, height, rotation_mode)
                        output_frame = texture_helper.read_texture(output_tex, width, height)
                    finally:
                        texture_helper.delete_texture(tex_id)
                    job["result"] = output_frame
                except Exception as exc:  # pylint: disable=broad-except
                    job["error"] = exc
                finally:
                    job["event"].set()
        if engine:
            engine.close()
        if texture_helper:
            texture_helper.close()
        if context:
            context.close()


class _GLTextureProcessor:
    """Uploads numpy frames to GL textures and reads processed textures back."""

    def __init__(self):
        self._fbo = GL.glGenFramebuffers(1)

    def upload_frame(self, frame: np.ndarray) -> tuple[int, int, int]:
        if frame.ndim != 3 or frame.shape[2] not in (3, 4):
            raise PixelFreeError("PixelFree 仅支持 3/4 通道图像")
        height, width = frame.shape[0], frame.shape[1]
        if frame.shape[2] == 3:
            rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        else:
            rgba = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)
        rgba = np.ascontiguousarray(rgba)

        tex_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, tex_id)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,
            GL.GL_RGBA,
            width,
            height,
            0,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
            rgba,
        )
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        return tex_id, width, height

    def read_texture(self, texture_id: int, width: int, height: int) -> np.ndarray:
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._fbo)
        GL.glFramebufferTexture2D(
            GL.GL_FRAMEBUFFER,
            GL.GL_COLOR_ATTACHMENT0,
            GL.GL_TEXTURE_2D,
            texture_id,
            0,
        )
        status = GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)
        if status != GL.GL_FRAMEBUFFER_COMPLETE:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
            raise PixelFreeError("读取纹理失败，帧缓冲不完整")
        buffer = GL.glReadPixels(
            0,
            0,
            width,
            height,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
        )
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        rgba = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        rgba = np.flipud(rgba)
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        return np.ascontiguousarray(bgr)

    def delete_texture(self, texture_id: Optional[int]):
        if texture_id:
            GL.glDeleteTextures([texture_id])

    def close(self):
        if self._fbo:
            GL.glDeleteFramebuffers(1, [self._fbo])
            self._fbo = None


class _OffscreenGLContext:
    """Creates a hidden GLFW window to host OpenGL context."""

    def __init__(self):
        if not glfw.init():
            raise PixelFreeError("初始化 GLFW 失败，无法创建 PixelFree 所需的 OpenGL 上下文。")
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_COMPAT_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, False)
        self._window = glfw.create_window(4, 4, "PixelFreeHidden", None, None)
        if not self._window:
            glfw.terminate()
            raise PixelFreeError("创建隐藏的 OpenGL 窗口失败。")

    def make_current(self):
        if self._window:
            glfw.make_context_current(self._window)

    def close(self):
        if self._window:
            glfw.destroy_window(self._window)
            self._window = None
        glfw.terminate()
