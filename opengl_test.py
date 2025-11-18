import glfw
from OpenGL.GL import glGetString, GL_VERSION

if not glfw.init():
    raise SystemExit("glfw.init failed")

glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_COMPAT_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.FALSE)

win = glfw.create_window(16, 16, "pf-test", None, None)
if not win:
    glfw.terminate()
    raise SystemExit("glfw.create_window failed")

glfw.make_context_current(win)
print("OpenGL version:", glGetString(GL_VERSION))

glfw.destroy_window(win)
glfw.terminate()
