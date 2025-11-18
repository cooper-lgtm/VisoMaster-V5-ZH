# PixelFree 美颜 SDK 使用说明

本文档介绍如何在 **VisoMaster-V5** 中启用并使用甲方提供的 PixelFreeEffects 美颜 SDK。所有步骤均以 Windows 环境为前提（SDK 官方仅支持 Windows + OpenGL）。

## 1. 准备运行环境

1. 将甲方提供的资源放入项目目录（或其它自选路径）：
   - `PixelFree.dll`
   - `pixelfreeAuth.lic`
   - 默认滤镜 `filter_model.bundle`（或自定义 bundle）
2. 推荐将上述文件集中放在 `dependencies/pixel_free/`，如：
   ```
   dependencies/pixel_free/
     ├── PixelFree.dll
     ├── pixelfreeAuth.lic
     └── filter_model.bundle
   ```
3. 如果你放在其他目录，也没有问题，只需在设置面板里更新路径并点击回车，系统会立即重新加载 SDK。

> ⚠️ 注意：没有授权文件或 DLL，SDK 将无法创建实例；日志窗口会提示“PixelFree 初始化失败”。

## 2. 在应用中启用 PixelFree

1. 启动 VisoMaster，打开右侧 **设置** → 找到新增的 **「PixelFree 美颜」** 分组。
2. 按需设置以下字段：
   - **PixelFree DLL 路径**：指向 `PixelFree.dll`
   - **授权文件路径**：指向 `pixelfreeAuth.lic`
   - **滤镜 bundle 路径**：指向 `filter_model.bundle`
   - 修改路径后按回车，软件会自动重载并提示成功或失败。
3. 勾选 **「启用 PixelFree 美颜」**，即可打开美颜流水线。
4. 若输入画面做了旋转（例如竖屏视频），请在 **输入旋转角度** 中选择对应角度，确保 SDK 能正确处理。

## 3. 常用参数说明

所有滑块的范围为 0~100，对应 SDK 的 0.0~1.0：

| 控件 | 对应 SDK 参数 | 说明 |
| ---- | ------------- | ---- |
| 滤镜名称 | `PFBeautyFiterName` | 填写 bundle 内置滤镜 ID，例如 `heibai1` |
| 滤镜强度 | `PFBeautyFiterStrength` | 控制滤镜整体强度 |
| 瘦脸 | `PFBeautyFiterTypeFace_thinning` | 面部瘦脸 |
| 磨皮 | `PFBeautyFiterTypeFaceBlurStrength` | 皮肤平滑 |
| 美白 | `PFBeautyFiterTypeFaceWhitenStrength` | 肤色提亮 |
| 红润 | `PFBeautyFiterTypeFaceRuddyStrength` | 面部红润度 |
| 亮眼 | `PFBeautyFiterTypeFaceEyeBrighten` | 眼睛提亮 |

你可以随时拖动滑块，帧处理线程会在下一帧自动同步参数，不需要额外的保存按钮。

## 4. 使用流程

1. 在 **PixelFree 美颜** 分组中设置好路径与参数，确保弹出“PixelFree 资源加载成功”的提示。
2. 在主界面加载图片 / 视频 / 摄像头流，开始换脸或增强流程。
3. 勾选「启用 PixelFree 美颜」，输出画面会在所有换脸与帧增强步骤完成后，再调用 SDK 对最终帧进行美颜处理。
4. 如需临时关闭美颜，可直接取消勾选开关，Pipeline 会自动绕过 SDK。

## 5. 常见问题

| 问题 | 处理方式 |
| ---- | -------- |
| Toast 提示 “仅支持 Windows” | SDK 无法在当前系统运行，需在 Windows 上执行 |
| 提示找不到 DLL/授权 | 检查路径是否填写正确、文件是否与 app 同一权限下 |
| 输出画面未变化 | 确认滑块值是否大于 0，并确保授权有效；查看终端是否有 PixelFree 相关错误 |
| 需要更换授权/滤镜 | 覆盖新文件后，重新在设置栏里输入路径并按回车重载即可 |

如需进一步调试，请参考 `docs/doc_windows.md`（官方文档）以及 `app/beauty/pixel_free_engine.py` 中的封装代码，可根据需要拓展更多美颜参数。
