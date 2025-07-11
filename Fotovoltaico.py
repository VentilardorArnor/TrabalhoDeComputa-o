import pygame
import pygame.freetype
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram
import numpy as np
from PIL import Image
import sys
import math

# Dicionário com as especificações dos painéis
PAINEL_SPECS = {
    610: {'size': np.array([2.4, 0.05, 1.3]), 'wattage': 610},
    330: {'size': np.array([2.0, 0.05, 1.0]), 'wattage': 330},
    160: {'size': np.array([1.5, 0.05, 0.7]), 'wattage': 160}
}

# --- Shaders ---
VERTEX_SHADER_DEPTH = """
#version 330 core
layout (location = 0) in vec3 aPos;
uniform mat4 lightSpaceMatrix;
uniform mat4 model;
void main() { gl_Position = lightSpaceMatrix * model * vec4(aPos, 1.0); }
"""
FRAGMENT_SHADER_DEPTH = """
#version 330 core
void main() { }
"""
VERTEX_SHADER_SHADOW = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec2 aTexCoords;
out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoords;
out vec4 FragPosLightSpace;
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;
uniform mat4 lightSpaceMatrix;
void main() {
    FragPos = vec3(model * vec4(aPos, 1.0));
    Normal = mat3(transpose(inverse(model))) * aNormal;
    TexCoords = aTexCoords;
    FragPosLightSpace = lightSpaceMatrix * vec4(FragPos, 1.0);
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}
"""
FRAGMENT_SHADER_SHADOW = """
#version 330 core
out vec4 FragColor;
in vec3 FragPos;
in vec3 Normal;
in vec2 TexCoords;
in vec4 FragPosLightSpace;
uniform sampler2D diffuseTexture;
uniform sampler2D shadowMap;
uniform vec3 lightPos;
uniform vec3 viewPos;
float calculateShadow(vec4 fragPosLightSpace, vec3 normal, vec3 lightDir) {
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;
    if(projCoords.z > 1.0) return 0.0;
    float closestDepth = texture(shadowMap, projCoords.xy).r; 
    float currentDepth = projCoords.z;
    float bias = max(0.05 * (1.0 - dot(normal, lightDir)), 0.005);
    float shadow = currentDepth - bias > closestDepth  ? 1.0 : 0.0;
    return shadow;
}
void main() {           
    vec3 color = texture(diffuseTexture, TexCoords).rgb;
    vec3 normal = normalize(Normal);
    vec3 lightColor = vec3(1.0);
    vec3 ambient = 0.25 * color;
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    float shadow = calculateShadow(FragPosLightSpace, normal, lightDir);
    vec3 lighting = (ambient + (1.0 - shadow) * diffuse) * color;    
    FragColor = vec4(lighting, 1.0);
}
"""
VERTEX_SHADER_SUN = """
#version 330 core
layout (location = 0) in vec3 aPos;
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;
void main() {
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}
"""
FRAGMENT_SHADER_SUN = """
#version 330 core
out vec4 FragColor;
void main() {
    FragColor = vec4(1.0, 1.0, 0.8, 1.0);
}
"""
# --- Classe da Câmera ---
class Camera:
    def __init__(self, position=np.array([0.0, 2.5, 8.0]), up=np.array([0.0, 1.0, 0.0]), yaw=-90.0, pitch=0.0):
        self.world_up = up; self.yaw = yaw; self.pitch = pitch
        self.movement_speed = 5.0; self.mouse_sensitivity = 0.1
        self.height = 2.5; self.position = position; self.position[1] = self.height
        self._update_camera_vectors()
    def get_view_matrix(self): return self._look_at(self.position, self.position + self.front, self.up)
    def process_keyboard(self, direction, delta_time):
        velocity = self.movement_speed * delta_time
        flat_front = np.array([self.front[0], 0.0, self.front[2]])
        if np.linalg.norm(flat_front) > 0: flat_front = flat_front / np.linalg.norm(flat_front)
        if direction == "FORWARD": self.position += flat_front * velocity
        if direction == "BACKWARD": self.position -= flat_front * velocity
        if direction == "LEFT": self.position -= self.right * velocity
        if direction == "RIGHT": self.position += self.right * velocity
        self.position[1] = self.height
    def process_mouse_movement(self, x_offset, y_offset, constrain_pitch=True):
        self.yaw += x_offset * self.mouse_sensitivity; self.pitch += y_offset * self.mouse_sensitivity
        if constrain_pitch:
            if self.pitch > 89.0: self.pitch = 89.0
            if self.pitch < -89.0: self.pitch = -89.0
        self._update_camera_vectors()
    def _update_camera_vectors(self):
        rad_yaw=np.radians(self.yaw); rad_pitch=np.radians(self.pitch)
        front=np.array([np.cos(rad_yaw)*np.cos(rad_pitch),np.sin(rad_pitch),np.sin(rad_yaw)*np.cos(rad_pitch)])
        self.front=front/np.linalg.norm(front)
        self.right=np.cross(self.front,self.world_up);self.right=self.right/np.linalg.norm(self.right)
        self.up=np.cross(self.right,self.front);self.up=self.up/np.linalg.norm(self.up)
    def _look_at(self, eye, target, up):
        z_axis = (eye-target);z_axis=z_axis/np.linalg.norm(z_axis); x_axis = np.cross(up,z_axis);x_axis=x_axis/np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis,x_axis)
        translation=np.identity(4,dtype=np.float32);translation[3,0:3]=-eye
        rotation=np.identity(4,dtype=np.float32);rotation[0,0:3]=x_axis;rotation[1,0:3]=y_axis;rotation[2,0:3]=z_axis
        return translation @ rotation

# --- Funções Auxiliares ---
def create_shader_program(vertex_src,fragment_src):
    try:return compileProgram(compileShader(vertex_src,GL_VERTEX_SHADER),compileShader(fragment_src,GL_FRAGMENT_SHADER))
    except Exception as e:print("ERRO:",e);pygame.quit();sys.exit()
def load_texture(path):
    try:
        img=Image.open(path);img_data=img.convert("RGBA").tobytes()
        texture_id=glGenTextures(1);glBindTexture(GL_TEXTURE_2D,texture_id)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,img.width,img.height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)
        glGenerateMipmap(GL_TEXTURE_2D);print(f"Textura '{path}' carregada.");return texture_id
    except Exception as e:print(f"ERRO text.: {path}-{e}");return -1
def perspective(fovy,aspect,near,far):f=1.0/np.tan(np.radians(fovy)/2.);return np.array([[f/aspect,0,0,0],[0,f,0,0],[0,0,(far+near)/(near-far),-1],[0,0,(2*far*near)/(near-far),0]],dtype=np.float32)
def ortho(left,right,bottom,top,near,far):return np.array([[2/(right-left),0,0,0],[0,2/(top-bottom),0,0],[0,0,-2/(far-near),0],[-(right+left)/(right-left),-(top+bottom)/(top-bottom),-(far+near)/(far-near),1]],dtype=np.float32)

# --- Funções de Geração de Geometria e Lógica ---
def generate_cylinder_vertices(radius=0.5, height=1.0, sides=16):
    vertices = []
    for i in range(sides):
        angle_i = (i / sides) * 2 * math.pi; angle_j = ((i + 1) / sides) * 2 * math.pi
        x_i, z_i = radius * math.cos(angle_i), radius * math.sin(angle_i); x_j, z_j = radius * math.cos(angle_j), radius * math.sin(angle_j)
        vertices.extend([x_i, height/2, z_i, x_i, 0, z_i, i/sides, 1]); vertices.extend([x_i, -height/2, z_i, x_i, 0, z_i, i/sides, 0]); vertices.extend([x_j, height/2, z_j, x_j, 0, z_j, (i+1)/sides, 1])
        vertices.extend([x_j, height/2, z_j, x_j, 0, z_j, (i+1)/sides, 1]); vertices.extend([x_i, -height/2, z_i, x_i, 0, z_i, i/sides, 0]); vertices.extend([x_j, -height/2, z_j, x_j, 0, z_j, (i+1)/sides, 0])
    for i in range(sides):
        angle_i = (i / sides) * 2 * math.pi; angle_j = ((i + 1) / sides) * 2 * math.pi
        x_i, z_i = radius * math.cos(angle_i), radius * math.sin(angle_i); x_j, z_j = radius * math.cos(angle_j), radius * math.sin(angle_j)
        vertices.extend([0, height/2, 0, 0, 1, 0, 0.5, 0.5]); vertices.extend([x_i, height/2, z_i, 0, 1, 0, x_i+0.5, z_i+0.5]); vertices.extend([x_j, height/2, z_j, 0, 1, 0, x_j+0.5, z_j+0.5])
        vertices.extend([0, -height/2, 0, 0, -1, 0, 0.5, 0.5]); vertices.extend([x_j, -height/2, z_j, 0, -1, 0, x_j+0.5, z_j+0.5]); vertices.extend([x_i, -height/2, z_i, 0, -1, 0, x_i+0.5, z_i+0.5])
    return np.array(vertices, dtype=np.float32)

def generate_sphere_vertices(radius=1.0, sectors=36, stacks=18):
    vertices_temp = []
    for i in range(stacks + 1):
        stack_angle = math.pi / 2 - i * math.pi / stacks; xy = radius * math.cos(stack_angle); y = radius * math.sin(stack_angle)
        for j in range(sectors + 1):
            sector_angle = j * 2 * math.pi / sectors
            x = xy * math.cos(sector_angle); z = xy * math.sin(sector_angle)
            nx, ny, nz = x/radius, y/radius, z/radius; u, v = j / sectors, i / stacks
            vertices_temp.extend([x, y, z, nx, ny, nz, u, v])
    indices = []; final_vertices = []
    for i in range(stacks):
        k1 = i * (sectors + 1); k2 = k1 + sectors + 1
        for j in range(sectors):
            if i != 0: indices.extend([k1 + j, k2 + j, k1 + j + 1])
            if i != (stacks - 1): indices.extend([k1 + j + 1, k2 + j, k2 + j + 1])
    for index in indices:
        final_vertices.extend(vertices_temp[index*8 : index*8+8])
    return np.array(final_vertices, dtype=np.float32)

# --- INÍCIO: DEFINIÇÃO GLOBAL DAS CONSTANTES DE GEOMETRIA ---
CUBE_VERTICES = np.array([-0.5,-0.5,-0.5,0,0,-1,0,0,.5,-0.5,-0.5,0,0,-1,1,0,.5,.5,-0.5,0,0,-1,1,1,.5,.5,-0.5,0,0,-1,1,1,-.5,.5,-0.5,0,0,-1,0,1,-.5,-0.5,-0.5,0,0,-1,0,0,-.5,-0.5,.5,0,0,1,0,0,.5,-0.5,.5,0,0,1,1,0,.5,.5,.5,0,0,1,1,1,.5,.5,.5,0,0,1,1,1,-.5,.5,.5,0,0,1,0,1,-.5,-0.5,.5,0,0,1,0,0,-.5,.5,.5,-1,0,0,1,0,-.5,.5,-0.5,-1,0,0,1,1,-.5,-0.5,-0.5,-1,0,0,0,1,-.5,-0.5,-0.5,-1,0,0,0,1,-.5,-0.5,.5,-1,0,0,0,0,-.5,.5,.5,-1,0,0,1,0,.5,.5,.5,1,0,0,1,0,.5,.5,-0.5,1,0,0,1,1,.5,-0.5,-0.5,1,0,0,0,1,.5,-0.5,-0.5,1,0,0,0,1,.5,-0.5,.5,1,0,0,0,0,.5,.5,.5,1,0,0,1,0,-.5,-0.5,-0.5,0,-1,0,0,1,.5,-0.5,-0.5,0,-1,0,1,1,.5,-0.5,.5,0,-1,0,1,0,.5,-0.5,.5,0,-1,0,1,0,-.5,-0.5,.5,0,-1,0,0,0,-.5,-0.5,-0.5,0,-1,0,0,1,-.5,.5,-0.5,0,1,0,0,1,.5,.5,-0.5,0,1,0,1,1,.5,.5,.5,0,1,0,1,0,.5,.5,.5,0,1,0,1,0,-.5,.5,.5,0,1,0,0,0,-.5,.5,-0.5,0,1,0,0,1],dtype=np.float32)
PLANE_VERTICES = np.array([[50.,0.,50.,0.,1.,0.,50.,50.],[-50.,0.,50.,0.,1.,0.,0.,50.],[-50.,0.,-50.,0.,1.,0.,0.,0.],[50.,0.,50.,0.,1.,0.,50.,50.],[-50.,0.,-50.,0.,1.,0.,0.,0.],[50.,0.,-50.,0.,1.,0.,50.,0.]],dtype=np.float32)
CYLINDER_VERTICES = generate_cylinder_vertices()
SPHERE_VERTICES = generate_sphere_vertices()
# --- FIM: DEFINIÇÃO GLOBAL DAS CONSTANTES DE GEOMETRIA ---

def calculate_sun_position(hour,radius=25.,height=30.):
    hour_angle=(hour-6.)/12.*math.pi
    if not(0<=hour_angle<=math.pi):return np.array([0.,-height,0.],dtype=np.float32)
    pos_x=10.;pos_y=math.sin(hour_angle)*height;pos_z=math.cos(hour_angle)*radius
    return np.array([pos_x,pos_y,pos_z],dtype=np.float32)

def setup_geometry():
    # Agora a função usa as constantes globais para criar os VAOs
    cubeVAO=glGenVertexArrays(1);glBindVertexArray(cubeVAO)
    cubeVBO=glGenBuffers(1);glBindBuffer(GL_ARRAY_BUFFER,cubeVBO);glBufferData(GL_ARRAY_BUFFER,CUBE_VERTICES.nbytes,CUBE_VERTICES,GL_STATIC_DRAW)
    glEnableVertexAttribArray(0);glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(0));glEnableVertexAttribArray(1);glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(12));glEnableVertexAttribArray(2);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(24))
    planeVAO=glGenVertexArrays(1);glBindVertexArray(planeVAO)
    planeVBO=glGenBuffers(1);glBindBuffer(GL_ARRAY_BUFFER,planeVBO);glBufferData(GL_ARRAY_BUFFER,PLANE_VERTICES.nbytes,PLANE_VERTICES,GL_STATIC_DRAW)
    glEnableVertexAttribArray(0);glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(0));glEnableVertexAttribArray(1);glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(12));glEnableVertexAttribArray(2);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(24))
    cylinderVAO=glGenVertexArrays(1);glBindVertexArray(cylinderVAO)
    cylinderVBO=glGenBuffers(1);glBindBuffer(GL_ARRAY_BUFFER,cylinderVBO);glBufferData(GL_ARRAY_BUFFER,CYLINDER_VERTICES.nbytes,CYLINDER_VERTICES,GL_STATIC_DRAW)
    glEnableVertexAttribArray(0);glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(0));glEnableVertexAttribArray(1);glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(12));glEnableVertexAttribArray(2);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(24))
    sphereVAO=glGenVertexArrays(1);glBindVertexArray(sphereVAO)
    sphereVBO=glGenBuffers(1);glBindBuffer(GL_ARRAY_BUFFER,sphereVBO);glBufferData(GL_ARRAY_BUFFER,SPHERE_VERTICES.nbytes,SPHERE_VERTICES,GL_STATIC_DRAW)
    glEnableVertexAttribArray(0);glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(0));glEnableVertexAttribArray(1);glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(12));glEnableVertexAttribArray(2);glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,32,ctypes.c_void_p(24))
    return cubeVAO, planeVAO, cylinderVAO, sphereVAO

def update_panel_positions(rows, cols):
    positions = []; spacing_x, spacing_z = 4.0, 5.0
    for i in range(rows):
        for j in range(cols):
            x = (j - (cols - 1) / 2.0) * spacing_x; z = (i - (rows - 1) / 2.0) * spacing_z - 10.0
            positions.append(np.array([x, 0, z]))
    return positions

def update_sign_texture(surface, font, texture_id, power_kw):
    temp_surface = pygame.Surface(surface.get_size()); background_color = (5, 5, 15); led_color = (150, 240, 255)
    temp_surface.fill(background_color)
    title_text = "GERACAO"; title_rect = font.get_rect(title_text, size=34); title_rect.centerx = temp_surface.get_rect().centerx; title_rect.top = 22
    font.render_to(temp_surface, title_rect, title_text, led_color)
    power_text = f"{power_kw:.2f} kW"; power_rect = font.get_rect(power_text, size=42); power_rect.centerx = temp_surface.get_rect().centerx; power_rect.top = 60
    font.render_to(temp_surface, power_rect, power_text, led_color)
    surface.fill(background_color)
    grid_size = 2; led_radius = 1
    for x in range(0, surface.get_width(), grid_size):
        for y in range(0, surface.get_height(), grid_size):
            pixel_color = temp_surface.get_at((x, y))
            if pixel_color != background_color: pygame.draw.circle(surface, led_color, (x, y), led_radius)
    texture_data = pygame.image.tostring(surface, "RGBA", True)
    glBindTexture(GL_TEXTURE_2D, texture_id); glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, surface.get_width(), surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

def draw_scene(shader, vao_dict, tex_dict, panel_positions, panel_specs, panel_tilt, panel_azimuth, battery_percentage):
    glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, tex_dict['grass']); glBindVertexArray(vao_dict['plane'])
    model = np.identity(4, dtype=np.float32); glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(PLANE_VERTICES))
    panel_size = panel_specs['size']
    for position in panel_positions:
        post_height = 2.
        glBindVertexArray(vao_dict['cylinder']); glBindTexture(GL_TEXTURE_2D, tex_dict['metal'])
        base_trans = np.identity(4, dtype=np.float32); base_trans[3, 0:3] = position
        sup_trans = np.identity(4, dtype=np.float32); sup_trans[3, 1] = post_height / 2.
        sup_scale = np.diag([.15, post_height, .15, 1.]).astype(np.float32)
        model = sup_scale @ sup_trans @ base_trans
        glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CYLINDER_VERTICES) // 8)
        glBindVertexArray(vao_dict['cube']); glBindTexture(GL_TEXTURE_2D, tex_dict['panel'])
        panel_trans = np.identity(4, dtype=np.float32); panel_trans[3, 1] = post_height
        tilt_rad = np.radians(panel_tilt); c_tilt, s_tilt = np.cos(tilt_rad), np.sin(tilt_rad)
        tilt_rot = np.array([[1, 0, 0, 0], [0, c_tilt, -s_tilt, 0], [0, s_tilt, c_tilt, 0], [0, 0, 0, 1]], dtype=np.float32)
        azimuth_rad = np.radians(panel_azimuth); c_az, s_az = np.cos(azimuth_rad), np.sin(azimuth_rad)
        azimuth_rot = np.array([[c_az, 0, s_az, 0], [0, 1, 0, 0], [-s_az, 0, c_az, 0], [0, 0, 0, 1]], dtype=np.float32)
        panel_scale = np.diag(list(panel_size) + [1.]).astype(np.float32)
        model = panel_scale @ tilt_rot @ azimuth_rot @ panel_trans @ base_trans
        glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CUBE_VERTICES) // 8)
    glBindVertexArray(vao_dict['cube']); glBindTexture(GL_TEXTURE_2D, tex_dict['metal'])
    battery_pos = np.array([2.5, 1.0, 1.0])
    base_trans = np.identity(4, dtype=np.float32); base_trans[3, 0:3] = battery_pos
    scale = np.diag([1.5, 2.0, 1.0, 1.0]).astype(np.float32); model = scale @ base_trans
    glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CUBE_VERTICES) // 8)
    BAR_MAX_HEIGHT = 1.8; BAR_WIDTH = 0.4
    glBindTexture(GL_TEXTURE_2D, tex_dict['red']); bar_pos = battery_pos + np.array([0, 0, 0.51])
    trans_mat = np.identity(4, dtype=np.float32); trans_mat[3, 0:3] = bar_pos
    scale_mat = np.diag([BAR_WIDTH, BAR_MAX_HEIGHT, 0.1, 1.0]).astype(np.float32); model = scale_mat @ trans_mat
    glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CUBE_VERTICES) // 8)
    if battery_percentage > 0:
        glBindTexture(GL_TEXTURE_2D, tex_dict['green'])
        current_bar_height = BAR_MAX_HEIGHT * (battery_percentage / 100.0)
        y_offset = (current_bar_height - BAR_MAX_HEIGHT) / 2.0; bar_pos_green = bar_pos + np.array([0, y_offset, 0.01])
        trans_mat_green = np.identity(4, dtype=np.float32); trans_mat_green[3, 0:3] = bar_pos_green
        scale_mat_green = np.diag([BAR_WIDTH, current_bar_height, 0.1, 1.0]).astype(np.float32); model = scale_mat_green @ trans_mat_green
        glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CUBE_VERTICES) // 8)
    glBindVertexArray(vao_dict['cube']); sign_pos = np.array([0, 0, 2.0]); glBindTexture(GL_TEXTURE_2D, tex_dict['metal'])
    post_trans = np.identity(4, dtype=np.float32); post_trans[3, 0:3] = sign_pos; post_trans[3, 1] = 1.25
    post_scale = np.diag([0.2, 2.5, 0.2, 1.0]).astype(np.float32); model = post_scale @ post_trans
    glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CUBE_VERTICES) // 8)
    glBindTexture(GL_TEXTURE_2D, tex_dict['sign'])
    board_trans = np.identity(4, dtype=np.float32); board_trans[3, 0:3] = sign_pos; board_trans[3, 1] = 3.2
    board_scale = np.diag([3.0, 1.5, 0.2, 1.0]).astype(np.float32); model = board_scale @ board_trans
    glUniformMatrix4fv(glGetUniformLocation(shader, "model"), 1, GL_FALSE, model); glDrawArrays(GL_TRIANGLES, 0, len(CUBE_VERTICES) // 8)

def render_text(text, font, pos, screen_width, screen_height):
    glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity(); glOrtho(0,screen_width,0,screen_height,-1,1)
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity(); glDisable(GL_DEPTH_TEST);glEnable(GL_BLEND);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
    font.render_to(pygame.display.get_surface(),pos,text,(255,255,255))
    glDisable(GL_BLEND);glEnable(GL_DEPTH_TEST); glMatrixMode(GL_PROJECTION);glPopMatrix(); glMatrixMode(GL_MODELVIEW);glPopMatrix()

def main():
    pygame.init(); pygame.freetype.init()
    screen_width,screen_height=1280,720
    pygame.display.set_mode((screen_width,screen_height),DOUBLEBUF|OPENGL)
    pygame.mouse.set_visible(False);pygame.event.set_grab(True)
    hud_font = pygame.freetype.SysFont("Arial", 24)
    try: sign_font = pygame.freetype.SysFont("Consolas", 48)
    except: sign_font = pygame.freetype.SysFont("Courier New", 48)
    SIGN_WIDTH, SIGN_HEIGHT = 256, 128; sign_surface = pygame.Surface((SIGN_WIDTH, SIGN_HEIGHT))
    sign_texture = glGenTextures(1); glBindTexture(GL_TEXTURE_2D, sign_texture); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST); glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SIGN_WIDTH, SIGN_HEIGHT, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    
    hora_atual=12.0; tipo_painel_selecionado=610; num_rows,num_cols=2,3
    panel_tilt_angle=20.0; panel_azimuth_angle = 0.0
    battery_capacity_kwh = 50.0; battery_current_kwh = 40.0; battery_max_charge_kw = 15.0
    farm_power_load_kw = 2.0
    
    shaders={'depth':create_shader_program(VERTEX_SHADER_DEPTH,FRAGMENT_SHADER_DEPTH),'shadow':create_shader_program(VERTEX_SHADER_SHADOW,FRAGMENT_SHADER_SHADOW), 'sun': create_shader_program(VERTEX_SHADER_SUN, FRAGMENT_SHADER_SUN)}
    textures={'grass':load_texture("grass.png"),'panel':load_texture("solar_cell.png"), 'metal':load_texture("metal_frame.png"), 'sign': sign_texture, 'red': load_texture("red.png"), 'green': load_texture("green.png")}
    if -1 in textures.values():pygame.quit();sys.exit()

    cube_vao, plane_vao, cylinder_vao, sphere_vao = setup_geometry()
    vaos = {'cube': cube_vao, 'plane': plane_vao, 'cylinder': cylinder_vao, 'sphere': sphere_vao}
    panel_positions=update_panel_positions(num_rows,num_cols)
    
    SHADOW_WIDTH,SHADOW_HEIGHT=2048,2048; depthMapFBO=glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER,depthMapFBO); depthMap=glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D,depthMap); glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,SHADOW_WIDTH,SHADOW_HEIGHT,0,GL_DEPTH_COMPONENT,GL_FLOAT,None)
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_BORDER);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_BORDER)
    borderColor=np.array([1.,1.,1.,1.],dtype=np.float32);glTexParameterfv(GL_TEXTURE_2D,GL_TEXTURE_BORDER_COLOR,borderColor)
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,depthMap,0)
    glDrawBuffer(GL_NONE);glReadBuffer(GL_NONE)
    if glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE:print("ERRO FBO!");pygame.quit();sys.exit()
    glBindFramebuffer(GL_FRAMEBUFFER,0)
    
    camera=Camera(); clock=pygame.time.Clock()
    glUseProgram(shaders['shadow']); glUniform1i(glGetUniformLocation(shaders['shadow'],"diffuseTexture"),0); glUniform1i(glGetUniformLocation(shaders['shadow'],"shadowMap"),1)
    glEnable(GL_DEPTH_TEST)
    
    while True:
        delta_time=clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type==pygame.QUIT or(event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):pygame.quit();return
            if event.type==pygame.MOUSEMOTION: camera.process_mouse_movement(-event.rel[0], -event.rel[1])
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_UP:hora_atual=(hora_atual+0.5)%24.
                if event.key==pygame.K_DOWN:hora_atual=(hora_atual-0.5+24.)%24.
                if event.key==pygame.K_1:tipo_painel_selecionado=160
                if event.key==pygame.K_2:tipo_painel_selecionado=330
                if event.key==pygame.K_3:tipo_painel_selecionado=610
                if event.key==pygame.K_EQUALS or event.key==pygame.K_PLUS: num_cols=min(10,num_cols+1);panel_positions=update_panel_positions(num_rows,num_cols)
                if event.key==pygame.K_MINUS: num_cols=max(1,num_cols-1);panel_positions=update_panel_positions(num_rows,num_cols)
                if event.key == pygame.K_q: panel_azimuth_angle = (panel_azimuth_angle - 5.0) % 360
                if event.key == pygame.K_e: panel_azimuth_angle = (panel_azimuth_angle + 5.0) % 360

        keys=pygame.key.get_pressed()
        if keys[pygame.K_w]:camera.process_keyboard("FORWARD",delta_time)
        if keys[pygame.K_s]:camera.process_keyboard("BACKWARD",delta_time)
        if keys[pygame.K_a]:camera.process_keyboard("LEFT",delta_time)
        if keys[pygame.K_d]:camera.process_keyboard("RIGHT",delta_time)

        sun_max_height = 30.0
        lightPos=calculate_sun_position(hora_atual, height=sun_max_height)
        specs_do_painel = PAINEL_SPECS[tipo_painel_selecionado]
        irradiance_factor = max(0, lightPos[1] / sun_max_height)
        tilt_rad=np.radians(panel_tilt_angle); initial_normal = np.array([0, np.cos(tilt_rad), np.sin(tilt_rad)])
        azimuth_rad = np.radians(panel_azimuth_angle); c, s = np.cos(azimuth_rad), np.sin(azimuth_rad)
        azimuth_rot_mat = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        panel_normal = azimuth_rot_mat @ initial_normal
        light_dir=lightPos-np.array([0,2,0]);light_dir=light_dir/np.linalg.norm(light_dir)
        angular_efficiency=max(0,np.dot(panel_normal,light_dir))
        total_efficiency = angular_efficiency * irradiance_factor
        total_power_kw = (len(panel_positions)*specs_do_painel['wattage']*total_efficiency) / 1000.0
        
        net_power_kw = total_power_kw - farm_power_load_kw
        if net_power_kw > 0:
            charge_power_kw = min(net_power_kw, battery_max_charge_kw)
            energy_change_kwh = charge_power_kw * (delta_time / 3600.0)
            battery_current_kwh += energy_change_kwh; battery_status = "CARREGANDO"
        else:
            energy_change_kwh = abs(net_power_kw) * (delta_time / 3600.0)
            battery_current_kwh -= energy_change_kwh; battery_status = "DESCARREGANDO"
        if battery_current_kwh <= 0:
            battery_current_kwh = 0
            if net_power_kw < 0: battery_status = "SEM ENERGIA" 
        if battery_current_kwh >= battery_capacity_kwh:
            battery_current_kwh = battery_capacity_kwh
            if net_power_kw > 0: battery_status = "CARGA MÁXIMA"
        
        battery_percentage = (battery_current_kwh / battery_capacity_kwh) * 100
        update_sign_texture(sign_surface, sign_font, textures['sign'], total_power_kw)

        projection=perspective(45.0,screen_width/screen_height,0.1,100.0); view=camera.get_view_matrix()
        lightProjection=ortho(-40.0,40.0,-40.0,40.0,1.0,80.0); lightView=camera._look_at(lightPos,np.array([0.,0.,0.]),np.array([0.,1.,0.]))
        lightSpaceMatrix=lightView@lightProjection
        glUseProgram(shaders['depth']);glUniformMatrix4fv(glGetUniformLocation(shaders['depth'],"lightSpaceMatrix"),1,GL_FALSE,lightSpaceMatrix)
        glViewport(0,0,SHADOW_WIDTH,SHADOW_HEIGHT);glBindFramebuffer(GL_FRAMEBUFFER,depthMapFBO);glClear(GL_DEPTH_BUFFER_BIT)
        draw_scene(shaders['depth'],vaos,textures,panel_positions,specs_do_painel,panel_tilt_angle, panel_azimuth_angle, battery_percentage)
        glBindFramebuffer(GL_FRAMEBUFFER,0)

        glViewport(0,0,screen_width,screen_height); glClearColor(0.5,0.8,1.0,1.0); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glUseProgram(shaders['shadow'])
        glUniformMatrix4fv(glGetUniformLocation(shaders['shadow'],"projection"),1,GL_FALSE,projection); glUniformMatrix4fv(glGetUniformLocation(shaders['shadow'],"view"),1,GL_FALSE,view)
        glUniform3fv(glGetUniformLocation(shaders['shadow'],"viewPos"),1,camera.position); glUniform3fv(glGetUniformLocation(shaders['shadow'],"lightPos"),1,lightPos)
        glUniformMatrix4fv(glGetUniformLocation(shaders['shadow'],"lightSpaceMatrix"),1,GL_FALSE,lightSpaceMatrix)
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,depthMap)
        draw_scene(shaders['shadow'],vaos,textures,panel_positions,specs_do_painel,panel_tilt_angle, panel_azimuth_angle, battery_percentage)

        glDepthMask(GL_FALSE)
        glUseProgram(shaders['sun'])
        glUniformMatrix4fv(glGetUniformLocation(shaders['sun'], "projection"), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(shaders['sun'], "view"), 1, GL_FALSE, view)
        trans_mat = np.identity(4, dtype=np.float32); trans_mat[3, 0:3] = lightPos
        scale_mat = np.diag([2.0, 2.0, 2.0, 1.0]).astype(np.float32)
        model_sun = scale_mat @ trans_mat
        glUniformMatrix4fv(glGetUniformLocation(shaders['sun'], "model"), 1, GL_FALSE, model_sun)
        glBindVertexArray(vaos['sphere'])
        glDrawArrays(GL_TRIANGLES, 0, len(SPHERE_VERTICES)//8)
        glDepthMask(GL_TRUE)

        minutos=int((hora_atual%1)*60)
        pygame.display.set_caption(f"Fazenda | Hora: {int(hora_atual):02d}:{minutos:02d} | Painel: {tipo_painel_selecionado}W | Azimute: {panel_azimuth_angle:.1f}°")
        render_text(f"Geração Placas: {total_power_kw:.2f} kW",hud_font,(10,screen_height-30),screen_width,screen_height)
        render_text(f"Consumo Fazenda: {farm_power_load_kw:.2f} kW",hud_font,(10,screen_height-60),screen_width,screen_height)
        render_text(f"Bateria: {battery_current_kwh:.2f}/{battery_capacity_kwh:.1f} kWh ({battery_percentage:.1f}%)", hud_font, (10, screen_height - 90), screen_width, screen_height)
        render_text(f"Status: {battery_status}", hud_font, (10, screen_height - 120), screen_width, screen_height)

        pygame.display.flip()

if __name__ == '__main__':
    main()
