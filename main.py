from PIL import Image
import math
import sys

import OpenGL
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Variáveis globais

window_width = 800
window_height = 600

# Variáveis para transformações
panel_rotation_angle = 0.0
system_translation_x = 0.0
system_translation_z = 0.0
system_scale = 1.0

# Variável para a posição da luz (simulando o sol)
light_position = [0.0, 10.0, 10.0, 1.0] # Posição inicial do sol (x, y, z, w - 1.0 para luz pontual, 0.0 para direcional)

# Variáveis para Shadow Mapping
shadow_map_texture = None
shadow_map_fbo = None
shadow_map_size = 1024

light_projection_matrix = None
light_view_matrix = None

# Variáveis para texturas
metallic_texture_id = None
solar_cell_texture_id = None
grass_texture_id = None

# Variável para simulação de energia
energy_generated = 0.0

def load_texture(path):
    img = Image.open(path)
    img_data = img.tobytes("raw", "RGBX", 0, -1) if img.mode == 'RGBA' else img.tobytes("raw", "RGB", 0, -1)

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    if img.mode == 'RGBA':
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    else:
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

    return texture_id

def draw_solar_panel():
    # Painel principal
    glPushMatrix()
    glScalef(2.0, 0.1, 1.0)  # Largura, espessura, profundidade
    glColor3f(1.0, 1.0, 1.0)  # Cor branca para que a textura seja visível
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, metallic_texture_id)
    glutSolidCube(1.0)
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()

    # Células solares (simuladas com uma superfície mais clara)
    glPushMatrix()
    glTranslatef(0.0, 0.051, 0.0) # Levemente acima do painel principal
    glScalef(1.9, 0.01, 0.9) # Um pouco menor que o painel principal
    glColor3f(1.0, 1.0, 1.0) # Cor branca para que a textura seja visível
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, solar_cell_texture_id)
    glutSolidCube(1.0)
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()

def draw_support_structure():
    # Exemplo de uma estrutura de suporte simples (um pilar)
    glPushMatrix()
    glTranslatef(0.0, -0.5, 0.0) # Abaixo do painel
    glScalef(0.1, 1.0, 0.1) # Largura, altura, profundidade
    glColor3f(0.5, 0.5, 0.5) # Cinza para a estrutura
    glutSolidCube(1.0)
    glPopMatrix()

def draw_photovoltaic_system():
    glPushMatrix()
    # Aplicar transformações globais ao sistema
    glTranslatef(system_translation_x, 0.5, system_translation_z) # Eleva o sistema do chão e aplica translação
    glScalef(system_scale, system_scale, system_scale) # Aplica escala

    # Aplicar rotação ao painel solar
    glPushMatrix()
    glRotatef(panel_rotation_angle, 1.0, 0.0, 0.0) # Rotação em torno do eixo X para simular o rastreador
    draw_solar_panel()
    glPopMatrix()

    draw_support_structure()
    glPopMatrix()

def render_scene_from_light():
    global light_projection_matrix, light_view_matrix

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    # Projeção ortográfica para luz direcional
    glOrtho(-10.0, 10.0, -10.0, 10.0, 0.1, 50.0)
    light_projection_matrix = glGetDoublev(GL_PROJECTION_MATRIX)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    # Posição da luz como a câmera
    gluLookAt(light_position[0], light_position[1], light_position[2],
              0.0, 0.0, 0.0,  # Olhando para o centro da cena
              0.0, 1.0, 0.0) # Up vector
    light_view_matrix = glGetDoublev(GL_MODELVIEW_MATRIX)

    # Prevenir "shadow acne"
    glEnable(GL_POLYGON_OFFSET_FILL)
    glPolygonOffset(2.0, 4.0)

    # Renderizar apenas a profundidade
    glDisable(GL_LIGHTING)
    glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)

    # Desenhar o chão
    glBegin(GL_QUADS)
    glVertex3f(-10.0, 0.0, -10.0)
    glVertex3f(-10.0, 0.0, 10.0)
    glVertex3f(10.0, 0.0, 10.0)
    glVertex3f(10.0, 0.0, -10.0)
    glEnd()

    # Desenhar o sistema fotovoltaico
    draw_photovoltaic_system()

    # Desabilitar o offset
    glDisable(GL_POLYGON_OFFSET_FILL)

    glEnable(GL_LIGHTING)
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def calculate_energy():
    global energy_generated
    # Simplificação: a energia gerada é máxima quando o painel está perpendicular à luz
    # A luz está vindo de light_position
    # O painel está rotacionado em torno do eixo X (panel_rotation_angle)

    # Vetor normal do painel (assumindo que inicialmente aponta para cima, [0, 1, 0])
    # Após rotação em torno do eixo X, a normal será [0, cos(angle), sin(angle)]
    # Convertendo para radianos
    angle_rad = math.radians(panel_rotation_angle)
    panel_normal_x = 0.0
    panel_normal_y = math.cos(angle_rad)
    panel_normal_z = math.sin(angle_rad)

    # Vetor da direção da luz (do objeto para a luz)
    # Como light_position é a posição da luz, o vetor direcional é (light_position - object_position)
    # Para luz direcional, a direção é constante, mas aqui estamos usando uma posição para simular
    # Para simplificar, vamos considerar a direção da luz como normalizada a partir da origem para light_position
    light_dir_x = light_position[0]
    light_dir_y = light_position[1]
    light_dir_z = light_position[2]
    light_dir_magnitude = math.sqrt(light_dir_x**2 + light_dir_y**2 + light_dir_z**2)
    if light_dir_magnitude > 0:
        light_dir_x /= light_dir_magnitude
        light_dir_y /= light_dir_magnitude
        light_dir_z /= light_dir_magnitude

    # Produto escalar entre a normal do painel e a direção da luz
    # Isso nos dá o cosseno do ângulo entre eles. Quanto mais próximo de 1, mais perpendicular.
    dot_product = (panel_normal_x * light_dir_x) + \
                  (panel_normal_y * light_dir_y) + \
                  (panel_normal_z * light_dir_z)

    # A energia é proporcional ao produto escalar, mas não pode ser negativa
    energy_factor = max(0.0, dot_product)

    # Multiplicar por um fator base para a energia
    energy_generated = energy_factor * 100.0 # Ex: 100 unidades de energia máxima

    glutPostRedisplay()

def keyboard(key, x, y):
    global panel_rotation_angle, system_translation_x, system_translation_z, system_scale

    if key == b'\x1b':  # ESC key
        glutLeaveMainLoop()
    elif key == b'r': # Rotacionar painel
        panel_rotation_angle += 5.0
        if panel_rotation_angle > 90.0:
            panel_rotation_angle = 90.0
        glutPostRedisplay()
    elif key == b'R': # Rotacionar painel (sentido inverso)
        panel_rotation_angle -= 5.0
        if panel_rotation_angle < 0.0:
            panel_rotation_angle = 0.0
        glutPostRedisplay()
    elif key == b'w': # Mover para frente (translação Z)
        system_translation_z -= 0.1
        glutPostRedisplay()
    elif key == b's': # Mover para trás (translação Z)
        system_translation_z += 0.1
        glutPostRedisplay()
    elif key == b'a': # Mover para esquerda (translação X)
        system_translation_x -= 0.1
        glutPostRedisplay()
    elif key == b'd': # Mover para direita (translação X)
        system_translation_x += 0.1
        glutPostRedisplay()
    elif key == b'+': # Aumentar escala
        system_scale += 0.1
        glutPostRedisplay()
    elif key == b'-': # Diminuir escala
        system_scale -= 0.1
        if system_scale < 0.1:
            system_scale = 0.1
        glutPostRedisplay()

def render_text(x, y, text, font):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_LIGHTING) # Desabilitar luz para o texto não ser afetado
    glColor3f(1.0, 1.0, 1.0) # Cor do texto (branco)
    glRasterPos2f(x, y)
    for character in text:
        glutBitmapCharacter(font, ord(character))
    glEnable(GL_LIGHTING)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def display():
    # --- PASSO 1: Renderizar a cena da perspectiva da luz para o mapa de profundidade ---
    glBindFramebuffer(GL_FRAMEBUFFER, shadow_map_fbo)
    glViewport(0, 0, shadow_map_size, shadow_map_size)
    glClear(GL_DEPTH_BUFFER_BIT)

    render_scene_from_light()

    glBindFramebuffer(GL_FRAMEBUFFER, 0) # Voltar para o framebuffer padrão

    # --- PASSO 2: Renderizar a cena da perspectiva da câmera, usando o mapa de profundidade para criar sombras ---
    glViewport(0, 0, window_width, window_height)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Configurar a matriz de textura para o shadow mapping
    # Esta matriz transforma as coordenadas do vértice do espaço do objeto para o espaço de textura da luz
    glMatrixMode(GL_TEXTURE)
    glLoadIdentity()
    # Matriz de bias para mapear de [-1, 1] para [0, 1]
    glTranslatef(0.5, 0.5, 0.5)
    glScalef(0.5, 0.5, 0.5)
    glMultMatrixd(light_projection_matrix)
    glMultMatrixd(light_view_matrix)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Posição da câmera
    gluLookAt(5, 5, 15, 0, 0, 0, 0, 1, 0)

    # Configurar a luz na cena principal
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)

    # Desenhar o chão com textura
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, grass_texture_id)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-20.0, 0.0, -20.0)
    glTexCoord2f(0.0, 20.0); glVertex3f(-20.0, 0.0, 20.0)
    glTexCoord2f(20.0, 20.0); glVertex3f(20.0, 0.0, 20.0)
    glTexCoord2f(20.0, 20.0); glVertex3f(20.0, 0.0, -20.0)
    glEnd()
    glDisable(GL_TEXTURE_2D)

    # Habilitar o shadow mapping
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, shadow_map_texture)
    glEnable(GL_TEXTURE_GEN_S)
    glEnable(GL_TEXTURE_GEN_T)
    glEnable(GL_TEXTURE_GEN_R)
    glEnable(GL_TEXTURE_GEN_Q)

    # Desenhar o sistema fotovoltaico (que irá receber e projetar sombras)
    draw_photovoltaic_system()

    # Desabilitar o shadow mapping
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_TEXTURE_GEN_S)
    glDisable(GL_TEXTURE_GEN_T)
    glDisable(GL_TEXTURE_GEN_R)
    glDisable(GL_TEXTURE_GEN_Q)

    calculate_energy()
    render_text(10, window_height - 30, f"Energia Gerada: {energy_generated:.2f} unidades", GLUT_BITMAP_HELVETICA_18)
    render_text(10, 10, "W/A/S/D: Mover | R/r: Rotacionar | +/-: Escala | ESC: Sair", GLUT_BITMAP_HELVETICA_12)
    glutSwapBuffers()

def init_gl():
    glClearColor(0.7, 0.7, 1.0, 1.0)  # Cor de fundo (céu azul claro)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # Configuração da luz direcional (sol)
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)  # Luz direcional

    # Propriedades do material para brilho especular
    glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
    glMaterialf(GL_FRONT, GL_SHININESS, 50.0)

    # Configuração do Shadow Map
    global shadow_map_texture, shadow_map_fbo

    # Criar textura para o mapa de profundidade
    shadow_map_texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, shadow_map_texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT, shadow_map_size, shadow_map_size, 0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    # Configurações para comparar a profundidade
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_R_TO_TEXTURE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL)

    # Criar Framebuffer Object (FBO) para renderizar o mapa de profundidade
    shadow_map_fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, shadow_map_fbo)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, shadow_map_texture, 0)
    glDrawBuffer(GL_NONE) # Não precisamos de buffer de cor
    glReadBuffer(GL_NONE) # Não precisamos de buffer de cor

    # Verificar se o FBO está completo
    if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
        print("Erro ao criar FBO para Shadow Map!")

    glBindFramebuffer(GL_FRAMEBUFFER, 0) # Voltar para o framebuffer padrão

    # Carregar texturas
    global metallic_texture_id, solar_cell_texture_id, grass_texture_id
    metallic_texture_id = load_texture("solar_panel_metallic.png")
    solar_cell_texture_id = load_texture("solar_cell_texture.png")
    grass_texture_id = load_texture("grass_texture.png")

def reshape(width, height):
    global window_width, window_height
    window_width = width
    window_height = height
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (width / height), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"Sistema Fotovoltaico 3D")

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)

    init_gl()
    glutMainLoop()

if __name__ == '__main__':
    main()
