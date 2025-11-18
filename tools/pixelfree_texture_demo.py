"""
Standalone PixelFree texture-mode demo for Windows.

Usage example (run from project root):
    wzf311\python.exe tools\pixelfree_texture_demo.py ^
        --dll lib/PixelFree.dll ^
        --auth res/pixelfreeAuth.lic ^
        --filter res/filter_model.bundle ^
        --image res/test.png

By default it assumes the same folder structure as SMBeautyEngine demo.
"""
from __future__ import annotations

import argparse
import ctypes
import os
from dataclasses import dataclass
from pathlib import Path

import glfw
import numpy as np
import cv2
from OpenGL import GL


class PFDetectFormat(ctypes.c_int):
    PFFORMAT_IMAGE_TEXTURE = 11


class PFRotationMode(ctypes.c_int):
    PFRotationMode0 = 0


class PFSrcType(ctypes.c_int):
    PFSrcTypeFilter = 0
    PFSrcTypeAuthFile = 2


class PFBeautyFiterType(ctypes.c_int):
    PFBeautyFiterName = 22
    PFBeautyFiterStrength = 23
    PFBeautyFiterTypeFaceBlurStrength = 15


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
class DemoConfig:
    dll_path: Path
    auth_path: Path
    filter_path: Path
    image_path: Path


def parse_args() -> DemoConfig:
    parser = argparse.ArgumentParser("PixelFree texture demo")
    parser.add_argument("--dll", required=False,
                        default="lib/PixelFree.dll", help="Path to PixelFree.dll")
    parser.add_argument("--auth", required=False,
                        default="res/pixelfreeAuth.lic", help="Auth license path")
    parser.add_argument("--filter", required=False,
                        default="res/filter_model.bundle", help="Filter bundle path")
    parser.add_argument("--image", required=False,
                        default="res/test.png", help="Test image path")
    args = parser.parse_args()
    return DemoConfig(
        dll_path=Path(args.dll).resolve(),
        auth_path=Path(args.auth).resolve(),
        filter_path=Path(args.filter).resolve(),
        image_path=Path(args.image).resolve(),
    )


def load_texture(image_path: Path) -> tuple[int, int, int]:
    bgr = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if bgr is None:
        raise RuntimeError(f"无法读取图片: {image_path}")
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    rgba = np.ascontiguousarray(rgba)
    height, width = rgba.shape[:2]

    tex_id = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, tex_id)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                    GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, rgba)
    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
    return tex_id, width, height


def set_parameter(func, handle, key: PFBeautyFiterType, value):
    if isinstance(value, str):
        func(handle, key, value.encode("utf-8"))
    else:
        func(handle, key, ctypes.byref(ctypes.c_float(float(value))))


def main():
    cfg = parse_args()
    for path in (cfg.dll_path, cfg.auth_path, cfg.filter_path, cfg.image_path):
        if not path.exists():
            raise FileNotFoundError(f"缺少文件: {path}")

    if not glfw.init():
        raise SystemExit("glfw.init failed")
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_COMPAT_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.FALSE)
    window = glfw.create_window(32, 32, "PixelFree demo", None, None)
    if not window:
        glfw.terminate()
        raise SystemExit("glfw.create_window failed")
    glfw.make_context_current(window)

    dll = ctypes.CDLL(str(cfg.dll_path))
    dll.PF_NewPixelFree.restype = ctypes.c_void_p
    dll.PF_processWithBuffer.restype = ctypes.c_int
    dll.PF_processWithBuffer.argtypes = [ctypes.c_void_p,
                                         ctypes.POINTER(PFIamgeInput)]
    dll.PF_createBeautyItemFormBundle.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    param_func = getattr(dll, "PF_pixelFreeSetBeautyFilterParam", None)
    if param_func is None:
        param_func = dll.PF_pixelFreeSetBeautyFiterParam
    param_func.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

    handle = dll.PF_NewPixelFree()
    if not handle:
        raise RuntimeError("PF_NewPixelFree 返回 NULL")

    for src, src_type in [(cfg.auth_path, PFSrcType.PFSrcTypeAuthFile),
                          (cfg.filter_path, PFSrcType.PFSrcTypeFilter)]:
        data = src.read_bytes()
        buffer = ctypes.create_string_buffer(data)
        dll.PF_createBeautyItemFormBundle(handle, buffer, len(data), src_type)

    set_parameter(param_func, handle, PFBeautyFiterType.PFBeautyFiterName, "heibai1")
    set_parameter(param_func, handle, PFBeautyFiterType.PFBeautyFiterStrength, 0.8)
    set_parameter(param_func, handle, PFBeautyFiterType.PFBeautyFiterTypeFaceBlurStrength, 0.4)

    tex_id, width, height = load_texture(cfg.image_path)

    input_img = PFIamgeInput()
    input_img.textureID = tex_id
    input_img.wigth = width
    input_img.height = height
    input_img.format = PFDetectFormat.PFFORMAT_IMAGE_TEXTURE
    input_img.rotationMode = PFRotationMode.PFRotationMode0
    input_img.p_data0 = None
    input_img.p_data1 = None
    input_img.p_data2 = None
    input_img.stride_0 = 0
    input_img.stride_1 = 0
    input_img.stride_2 = 0

    result = dll.PF_processWithBuffer(handle, ctypes.pointer(input_img))
    if result <= 0:
        raise RuntimeError(f"PF_processWithBuffer failed: {result}")
    print("PixelFree 处理成功，输出纹理 ID:", result)

    GL.glDeleteTextures([tex_id])
    glfw.destroy_window(window)
    glfw.terminate()


if __name__ == "__main__":
    main()
