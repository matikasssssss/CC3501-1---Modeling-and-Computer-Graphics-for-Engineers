import pyglet
import pyglet.gl as GL
import trimesh as tm
import numpy as np
import os
from pathlib import Path
import sys
import pymunk
import transformations as tr
from pyglet.window import key
import time
from OpenGL.GL import *
import OpenGL.GL.shaders
from gpu_shape import GPUShape
from utils import load_pipeline
from textures import texture_2D_setup

if sys.path[0] != "":
    sys.path.insert(0, "")
        

# código de arcball.py para leer un mesh
def setupMesh(file_path, tex_pipeline, notex_pipeline, scale): 
    # dependiendo de lo que contenga el archivo a cargar,
    # trimesh puede entregar una malla (mesh)
    # o una escena (compuesta de mallas)
    # con esto forzamos que siempre entregue una escena
    asset = tm.load(file_path, force="scene")

    # de acuerdo a la documentación de trimesh, esto centra la escena
    # no es igual a trabajar con una malla directamente
    asset.rezero()

    # y esto la escala con lo que decidamos, printea tambien un cubo en el que cae todo el modelo para tener como referencia
    asset = asset.scaled(scale / asset.scale)
    print(file_path)
    print(asset.bounds)

    # aquí guardaremos las mallas del modelo que graficaremos
    vertex_lists = {}

    # con esto iteramos sobre las mallas
    for object_id, object_geometry in asset.geometry.items():
        mesh = {}

        # por si acaso, para que la malla tenga normales consistentes
        object_geometry.fix_normals(True)

        object_vlist = tm.rendering.mesh_to_vertexlist(object_geometry)

        n_triangles = len(object_vlist[4][1]) // 3

        # el pipeline a usar dependerá de si el objeto tiene textura
        # OJO: asumimos que si tiene material, tiene textura
        # pero no siempre es así.
        if object_geometry.visual.material.image != None:
            print('has texture')
            mesh["pipeline"] = tex_pipeline
            has_texture = True
        else:
            print('no texture')
            mesh["pipeline"] = notex_pipeline
            has_texture = False

        # inicializamos los datos en la GPU
        mesh["gpu_data"] = mesh["pipeline"].vertex_list_indexed(
            n_triangles, GL.GL_TRIANGLES, object_vlist[3]
        )

        # copiamos la posición de los vértices
        mesh["gpu_data"].position[:] = object_vlist[4][1]

        # las normales vienen en vertex_list[5]
        # las manipulamos del mismo modo que los vértices
        mesh["gpu_data"].normal[:] = object_vlist[5][1]

        # con (o sin) textura es diferente el procedimiento
        # aunque siempre en vertex_list[6] viene la información de material
        if has_texture:
            # copiamos la textura
            # trimesh ya la cargó, solo debemos copiarla a la GPU
            # si no se usa trimesh, el proceso es el mismo,
            # pero se debe usar Pillow para cargar la imagen
            mesh["texture"] = texture_2D_setup(object_geometry.visual.material.image)
            # copiamos las coordenadas de textura en el parámetro uv
            mesh["gpu_data"].uv[:] = object_vlist[6][1]
        else:
            # usualmente el color viene como c4B/static en vlist[6][0], lo que significa "color de 4 bytes". idealmente eso debe verificarse
            mesh["gpu_data"].color[:] = object_vlist[6][1]
        mesh['id'] = object_id[0:-4]
        vertex_lists[object_id] = mesh
    return vertex_lists
class Controller:
    def __init__(self):
        self.ilumination = np.array([0.5, 0.5, 1.0])
        self.projection = tr.ortho(-1, 1,-1, 1, 0.1, 100).reshape(16, 1, order='F')
        self.view_active = False
        self.currentViewx = np.array([0, 0, 2])
        self.currentViewz = np.array([0, 1, 0])
    def toggleView(self):
        self.view_active = not self.view_active
        if self.view_active:
            self.projection = tr.perspective(40, window.width / window.height, 0.01, 100).reshape(16, 1, order='F')
            self.currentViewx = np.array([0, -2, 2])
            self.currentViewz = np.array([0, 0, 1])
        else:
            self.projection = tr.ortho(-1, 1,-1, 1, 0.1, 100).reshape(16, 1, order='F')
            self.currentViewx = np.array([0, 0, 2])
            self.currentViewz = np.array([0, 1, 0])

    def change_ilumination(self):
            self.ilumination = np.array([-0.1, -0.1, 1.0])
    def change_ilumination1(self):
            self.ilumination = np.array([0.5, 0.5, 1.0])


if __name__ == "__main__":
    width = 960
    height = 960
    window = pyglet.window.Window(width, height, 'flipperv2')
    controller = Controller()

    # como no todos los archivos que carguemos tendrán textura,
    # tendremos dos pipelines
    tex_pipeline = load_pipeline(   
        Path(os.path.dirname(__file__)) / "vertex_program.glsl",
        Path(os.path.dirname(__file__)) / "fragment_program.glsl",
    )

    notex_pipeline = load_pipeline(
        Path(os.path.dirname(__file__)) / "vertex_program_notex.glsl",
        Path(os.path.dirname(__file__)) / "fragment_program_notex.glsl",
    )

    vertex_lists = {}
    vertex_lists = setupMesh('./assets/flipper/base.obj', tex_pipeline, notex_pipeline, 2)
    vertex_lists = vertex_lists | setupMesh('./assets/flipper/objsextras.obj', tex_pipeline, notex_pipeline, 1.954)
    vertex_lists = vertex_lists | setupMesh('./assets/flipper/flipperder.obj', tex_pipeline, notex_pipeline, 0.15)
    vertex_lists = vertex_lists | setupMesh('./assets/flipper/flipperizq.obj', tex_pipeline, notex_pipeline, 0.15)
    vertex_lists = vertex_lists | setupMesh('./assets/flipper/pelota.obj', tex_pipeline, notex_pipeline, 0.085)
    

    # Creación del espacio físico
    space = pymunk.Space()
    space.gravity = (0, -0.5)
    #base
    vertices = [(0,0), (0,0), (0,0), (0,0)]
    base_body = pymunk.Body(body_type=pymunk.Body.STATIC) 
    base_shape = pymunk.Poly(base_body, vertices)
    base_body.position = (0, 0) 
    space.add(base_body, base_shape)
    #objsextras
    objsextras_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    objsextras_shape = pymunk.Poly(objsextras_body, vertices)
    objsextras_body.position = (0, 0)  
    objsextras_shape.elasticity = 0.95
    space.add(objsextras_body, objsextras_shape)
    #pelota
    ball_mass= 0.148
    ball_body = pymunk.Body(ball_mass, pymunk.moment_for_circle(ball_mass, 0.35, 0.35, (0,0)))
    ball_body.position = (0.4, -0.6)
    ball_shape = pymunk.Circle(ball_body, 0.035, (0,0))
    ball_shape.collision_type = 1
    ball_body.velocity = (0, 0)
    ball_shape.elasticity = 0.95
    space.add(ball_body, ball_shape)
    #flipperder
    vertices = [(0.07345884, 0.01322259), (-0.07345884, 0.01322259), (-0.07345884, -0.01322259), (0.07345884, -0.01322259)]
    centro_de_masa = (0, 0)
    flipperder_mass = 1
    flipperder_body = pymunk.Body(flipperder_mass, 
                           pymunk.moment_for_poly(flipperder_mass, vertices=vertices, offset=centro_de_masa))
    flipperder_body.center_of_gravity = centro_de_masa
    flipperder_body.position = (0.05, -0.68)  
    flipperder_body.angle = np.pi/4
    flipperder_shape = pymunk.Poly(flipperder_body,
                            vertices=vertices)
    flipperder_shape.collision_type = 3
    pivot_point_der = pymunk.PivotJoint(space.static_body, flipperder_body, flipperder_body.position + (0.03, 0.014))
    min_angle = np.pi/30  
    max_angle = np.pi/4  
    rotary_limit_der = pymunk.RotaryLimitJoint(space.static_body, flipperder_body, min_angle, max_angle)
    flipperder_shape.elasticity = 0.7
    space.add(flipperder_body, flipperder_shape, pivot_point_der, rotary_limit_der)
    #flipperizq
    vertices = [(0.07345884, 0.01322259), (-0.07345884, 0.01322259), (-0.07345884, -0.01322259), (0.07345884, -0.01322259)]
    centro_de_masa = (0, 0)
    flipperizq_mass = 1
    flipperizq_body = pymunk.Body(flipperizq_mass, 
                           pymunk.moment_for_poly(flipperizq_mass, vertices=vertices, offset=centro_de_masa))
    flipperizq_body.center_of_gravity = centro_de_masa
    flipperizq_body.position = (-0.15, -0.68)  
    flipperizq_body.angle = -np.pi/4
    flipperizq_shape = pymunk.Poly(flipperizq_body,
                            vertices=vertices)
    flipperizq_shape.collision_type = 3
    pivot_point_izq = pymunk.PivotJoint(space.static_body, flipperizq_body, flipperizq_body.position + (-0.03, 0.014))
    min_angle = -np.pi/4 
    max_angle = -np.pi/30  
    rotary_limit_izq = pymunk.RotaryLimitJoint(space.static_body, flipperizq_body, min_angle, max_angle)
    flipperizq_shape.elasticity = 0.7
    space.add(flipperizq_body, flipperizq_shape, pivot_point_izq,rotary_limit_izq)
    #cuerpo para los segmentos
    segment_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    space.add(segment_body)
    #limites
    #obstaculos
    obs1_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs1 = [(-0.3, 0.39), (-0.3, 0.39), (-0.06, 0.51),(-0.06, 0.51)]
    obs1_shape = pymunk.Poly(obs1_body, vertices_obs1)
    obs1_shape.collision_type = 2
    space.add(obs1_body,obs1_shape)
    obs2_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs2 = [(-0.03, 0.495),(-0.03, 0.49501),(0.2, 0.39), (0.2, 0.385)]
    obs2_shape = pymunk.Poly(obs2_body, vertices_obs2)
    obs2_shape.collision_type = 2
    space.add(obs2_body,obs2_shape)
    obs3_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs3 = [(-0.14, 0.14),(-0.139, 0.15),(-0.01, 0.042), (-0.005, 0.039)]
    obs3_shape = pymunk.Poly(obs3_body, vertices_obs3)
    obs3_shape.collision_type = 2
    space.add(obs3_body,obs3_shape)
    obs4_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs4 = [(0.092, -0.08),(0.092, -0.075),(0.168, 0.04), (0.18, 0.05)]
    obs4_shape = pymunk.Poly(obs4_body, vertices_obs4)
    obs4_shape.collision_type = 2
    space.add(obs4_body,obs4_shape)
    obs5_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs5 = [(0.248, -0.27),(0.253, -0.27),(0.253, -0.08), (0.248, -0.08)]
    obs5_shape = pymunk.Poly(obs5_body, vertices_obs5)
    obs5_shape.collision_type = 2
    space.add(obs5_body,obs5_shape)
    obs6_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs6 = [(0.2, -0.45),(0.21, -0.46),(0.2485, -0.3), (0.248, -0.3)]
    obs6_shape = pymunk.Poly(obs6_body, vertices_obs6)
    obs6_shape.collision_type = 2
    space.add(obs6_body,obs6_shape)
    obs7_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs7 = [(-0.3525, 0.09),(-0.345, 0.095),(-0.3, -0.03), (-0.305, -0.035)]
    obs7_shape = pymunk.Poly(obs7_body, vertices_obs7)
    obs7_shape.collision_type = 2
    space.add(obs7_body,obs7_shape)
    obs8_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_obs8 = [(-0.29, -0.03),(-0.285, -0.028),(-0.344, -0.215), (-0.345, -0.21)]
    obs8_shape = pymunk.Poly(obs8_body, vertices_obs8)
    obs8_shape.collision_type = 2
    space.add(obs8_body,obs8_shape)
    #lados
    segment1 = pymunk.Segment(segment_body, (-1, -1.39), (1, -1.39), 0.5) #ladoinf
    segment1.collision_type = 3
    segment2 = pymunk.Segment(segment_body, (-1, 1.39), (1, 1.39), 0.5) #ladosup
    segment2.collision_type = 3
    segment3 = pymunk.Segment(segment_body, (0.94, -1.39), (0.94, 1.39), 0.5) #ladoder
    segment3.collision_type = 3
    segment4 = pymunk.Segment(segment_body, (-0.94, -1.39), (-0.94, 1.39), 0.5) #ladoizq
    segment4.collision_type = 3
    segment2.elasticity = 0.35
    segment2.friction = 0.9
    segment3.elasticity = 0.35
    segment3.friction = 0.9
    segment4.elasticity = 0.35
    segment4.friction = 0.9
    space.add(segment1,segment2,segment3,segment4)
    #esquinas
    segment5 = pymunk.Segment(segment_body, (0.85, 1.12), (0.77, 1.2), 0.5) #esquina der sup
    segment5.collision_type = 3
    segment6 = pymunk.Segment(segment_body, (-0.85, 1.12), (-0.77, 1.2), 0.5) #esquina izq sup
    segment6.collision_type = 3
    #esquina derecha1, al lado de la esquina der sup
    trianesq_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trianesq = [(-0.21, 0.86), (-0.11, 0.86), (-0.11, 0.78)]
    trianesq_shape = pymunk.Poly(trianesq_body, vertices_trianesq)
    trianesq_shape.collision_type = 3
    space.add(trianesq_body,trianesq_shape)
    #pilar al lado de esquina derecha1
    pilar_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_pilar = [(-0.085, 0.86), (-0.085, 0.86), (-0.085, 0.78), (-0.085, 0.78)]
    pilar_shape = pymunk.Poly(pilar_body, vertices_pilar)
    pilar_shape.collision_type = 3
    space.add(pilar_body,pilar_shape)
    #esquina der que esta al lado del pilar
    trianesq1_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trianesq1 = [(-0.03, 0.86), (-0.1, 0.81)]
    trianesq1_shape = pymunk.Poly(trianesq1_body, vertices_trianesq1)
    trianesq1_shape.collision_type = 3
    space.add(trianesq1_body,trianesq1_shape)
    #esquina der que esta al lado de la recta horizontal de lanzamiento
    trianesq2_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trianesq2 = [(0.22, 0.76), (0.32, 0.66)]
    trianesq2_shape = pymunk.Poly(trianesq2_body, vertices_trianesq2)
    trianesq2_shape.collision_type = 3
    space.add(trianesq2_body,trianesq2_shape)
    #mas esquinas
    esq1_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_esq1 = [(-1, -1), (-1, -0.865), (-0.1, -0.895), (-0.1, -1)]
    esq1_shape = pymunk.Poly(esq1_body, vertices_esq1)
    esq1_shape.collision_type = 3
    esq2_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_esq2 = [(0.005, -1), (0.005, -0.865), (1, -0.865), (1, -1)]
    esq2_shape = pymunk.Poly(esq2_body, vertices_esq2)
    esq2_shape.collision_type = 3
    space.add(segment5, segment6, esq1_body,esq1_shape,esq2_body,esq2_shape)
    #objs de lanzamiento
    #recta horizontal
    rect_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_rect = [(0.34, -1), (0.34, 0.8), (0.36, 0.8), (0.36, -1)]
    rect_shape = pymunk.Poly(rect_body, vertices_rect)
    rect_shape.collision_type = 3
    rect_shape.elasticity = 0.6
    rect_shape.friction = 0.9
    #recta vertical
    rectA_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_rectA = [(0, 0.79), (0, 0.79), (0.3, 0.79), (0.3, 0.79)]
    rectA_shape = pymunk.Poly(rectA_body, vertices_rectA)
    rectA_shape.collision_type = 3
    #base lanzamiento
    lanzamiento_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_lanz = [(0.36, -1),(0.36, -0.655), (0.5,-0.655),(0.5,-1)]
    lanzamiento_shape = pymunk.Poly(lanzamiento_body, vertices_lanz)
    lanzamiento_shape.collision_type = 3
    space.add(rectA_body, rectA_shape, rect_body, rect_shape,lanzamiento_body,lanzamiento_shape)

    #objs interactivos
    #trian izq
    #1st trian
    trian_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trian = [(-0.6, -0.2), (-0.5, -0.01), (-0.39, -0.52)]
    trian_shape = pymunk.Poly(trian_body, vertices_trian)
    trian_shape.collision_type = 3
    trian_shape.elasticity = 0.5
    trian_shape.friction = 0.9
    space.add(trian_body, trian_shape)
    #2nd trian
    trian2_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trian2 = [(-0.7, -1), (-0.4, -0.49), (-0.18, -0.82)]
    trian2_shape = pymunk.Poly(trian2_body, vertices_trian2)
    trian2_shape.collision_type = 3
    trian2_shape.elasticity = 0.5
    trian2_shape.friction = 0.9
    space.add(trian2_body, trian2_shape)
    #3nd trian
    trian6_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trian6 = [(-0.1, -0.89), (-0.2, -0.8), (-0.02, -0.93)]
    trian6_shape = pymunk.Poly(trian6_body, vertices_trian6)
    trian6_shape.collision_type = 4
    trian6_shape.elasticity = 0.5
    trian6_shape.friction = 0.9
    space.add(trian6_body, trian6_shape)

    #trian der
    #1st trian
    trian3_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trian3 = [(0.41, -0.05), (0.41, -0.53), (0.28, -0.53)]
    trian3_shape = pymunk.Poly(trian3_body, vertices_trian3)
    trian3_shape.collision_type = 3
    trian3_shape.elasticity = 0.5
    trian3_shape.friction = 0.9
    space.add(trian3_body, trian3_shape)
    #2nd trian
    trian4_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trian4 = [(0.28, -0.53), (0.28, -0.79), (0.1, -0.79)]
    trian4_shape = pymunk.Poly(trian4_body, vertices_trian4)
    trian4_shape.collision_type = 3
    trian4_shape.elasticity = 0.5
    trian4_shape.friction = 0.9
    space.add(trian4_body, trian4_shape)
    #3nd trian
    trian5_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_trian5 = [(0.1, -0.79), (0.28, -0.79), (0.01, -0.89)]
    trian5_shape = pymunk.Poly(trian5_body, vertices_trian5)
    trian5_shape.collision_type = 5
    trian5_shape.elasticity = 0.5
    trian5_shape.friction = 0.9
    space.add(trian5_body, trian5_shape)

    #flip1
    flip_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_flip = [(-0.36, -0.57), (-0.36, -0.56), (-0.215, -0.605),(-0.22, -0.612)]
    flip_shape = pymunk.Poly(flip_body, vertices_flip)
    flip_shape.collision_type = 7
    space.add(flip_body,flip_shape)
    #flip2
    flip1_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    vertices_flip1 = [(0.11, -0.615), (0.11, -0.615), (0.4, -0.53),(0.4, -0.53)]
    flip1_shape = pymunk.Poly(flip1_body, vertices_flip1)
    flip1_shape.collision_type = 3
    space.add(flip1_body,flip1_shape)
    def collision_handler1(arbiter, space, data):
        print("La pelota ha chocado con los obstaculos!")
        controller.change_ilumination()
        return True
    def collision_handler2(arbiter, space, data):
        print("La pelota ha chocado con los objetos extras")
        controller.change_ilumination1()
        return True
    def collision_handler3(arbiter, space, data):
        print("La pelota ha chocado con los objetos extras")
        controller.change_ilumination1()
        ball_body.velocity = (0.1,0)
        return True
    def collision_handler4(arbiter, space, data):
        print("La pelota ha chocado con los objetos extras")
        controller.change_ilumination1()
        ball_body.velocity = (-0.1,0)
        return True


    
    handler1 = space.add_collision_handler(1, 2)
    handler1.begin = collision_handler1
    handler2 = space.add_collision_handler(1, 3)
    handler2.begin = collision_handler2
    handler3 = space.add_collision_handler(1, 4)
    handler3.begin = collision_handler3
    handler4 = space.add_collision_handler(1, 5)
    handler4.begin = collision_handler4


    # Diccionario para mantener la relación entre cuerpos físicos y objetos de renderizado
    bodies = {}
    bodies['base'] = base_body
    bodies['objsextras'] = objsextras_body
    bodies['flipperder'] = flipperder_body
    bodies['flipperizq'] = flipperizq_body
    bodies['pelota'] = ball_body
    
    smoothness = 10
    @window.event
    def on_key_press(key, modifier):
        if key == pyglet.window.key.A:
            flipperizq_body.angular_velocity = 25
        if key == pyglet.window.key.D:
            flipperder_body.angular_velocity = -25
        if key == pyglet.window.key.C:
            controller.toggleView()
        
    @window.event
    def on_key_release(key, modifier):
        if key == pyglet.window.key.A:
            angle_diff = 0 - flipperizq_body.angle  
            flipperizq_body.angular_velocity = angle_diff * smoothness
        if key == pyglet.window.key.D:
            angle_diff = 0 - flipperder_body.angle 
            flipperder_body.angular_velocity = -angle_diff * smoothness
        if key == pyglet.window.key.SPACE:
            if 0.36 < ball_body.position[0] < 0.5:
                ball_body.velocity = (0, 70)
    @window.event
    def on_draw():
        GL.glClearColor(138/255, 57/255, 153/255, 1.0)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glLineWidth(1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        window.clear()

        done = False
        for i in range(10):
            pos = ball_body.position
            #print(f"La posición de la pelota es {pos[0]}, {pos[1]}")
            
            if pos[1]  < -0.16 and pos[1] < -0.845:
                    pyglet.app.exit()
                    done = True
            space.step(1.0/60 / 10)
        if done == True:
            print("GAME OVER!")

        for object_geometry in vertex_lists.values():
            # Dibujamos cada uno de los objetos con su respectivo pipeline
            pipeline = object_geometry["pipeline"]
            pipeline.use()
            #fuente de luz uno
            pipeline['light_position1'] = controller.ilumination
            pipeline['light_position2'] = np.array([0.3, 0.5, 1.0])
            pipeline['La1'] = np.array([1.0, 1.0, 1.0])
            pipeline['Ld1'] = np.array([1.0, 1.0, 1.0])
            pipeline['Ls1'] = np.array([1.0, 1.0, 1.0])
            pipeline['La2'] = np.array([0.5, 0.0, 0.5])
            pipeline['Ld2'] = np.array([0.7, 0.0, 0.7])
            pipeline['Ls2'] = np.array([1.0, 0.0, 1.0])
            pipeline['Ka'] = np.array([0.19225, 0.19225, 0.19225])
            pipeline['Kd'] = np.array([0.50754, 0.50754, 0.50754])
            pipeline['Ks'] = np.array([0.508273, 0.508273, 0.508273])
            pipeline['shininess'] = 0.4
            pipeline['constantAttenuation'] = 1.0
            pipeline['linearAttenuation'] = 0.045
            pipeline['quadraticAttenuation'] = 0.0075
            pipeline['viewPosition'] = np.array([0.0, 0.0, 0.0])

            # Recuperamos las variables de los cuerpos físicos para la transformación que dibujará los modelos
            z = 0
            x, y = bodies[object_geometry['id']].position
            if object_geometry['id'] in ['pelota']:
                z = 0  
            if object_geometry['id'] in ['flipperizq']:
                z = -0.01 
                alpha = bodies[object_geometry['id']].angle
                pipeline["transform"] = (tr.translate(x, y, z) @ tr.rotationZ(alpha) @ tr.rotationX(np.pi/2)).reshape(16, 1, order="F")
                pipeline['projection'] = controller.projection
                pipeline['view'] = tr.lookAt(controller.currentViewx, np.array([0, 0, 0]), controller.currentViewz).reshape(16, 1, order='F')
            if object_geometry['id'] in ['flipperder']:
                z = -0.01 
                alpha = bodies[object_geometry['id']].angle
                pipeline["transform"] = (tr.translate(x, y, z) @ tr.rotationZ(alpha) @ tr.rotationX(np.pi/2)).reshape(16, 1, order="F")
                pipeline['projection'] = controller.projection
                pipeline['view'] = tr.lookAt(controller.currentViewx, np.array([0, 0, 0]), controller.currentViewz).reshape(16, 1, order='F')
            if object_geometry['id'] in ['base','pelota']:
                pipeline["transform"] = (tr.translate(x, y, z) @ tr.rotationX(-np.pi) @ tr.rotationZ(-np.pi/2)).reshape(16, 1, order="F")
                pipeline['projection'] = controller.projection
                pipeline['view'] = tr.lookAt(controller.currentViewx, np.array([0, 0, 0]), controller.currentViewz).reshape(16, 1, order='F')
            if object_geometry['id'] in ['objsextras']:
                pipeline["transform"] = (tr.translate(x, y, z) @ tr.rotationZ(np.pi/2) @ tr.rotationX(np.pi)).reshape(16, 1, order="F")
                pipeline['projection'] = controller.projection
                pipeline['view'] = tr.lookAt(controller.currentViewx, np.array([0, 0, 0]), controller.currentViewz).reshape(16, 1, order='F')

            if "texture" in object_geometry:
                GL.glBindTexture(GL.GL_TEXTURE_2D, object_geometry["texture"])
            else:
                # Esto "activa" una textura nula
                GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

            object_geometry["gpu_data"].draw(pyglet.gl.GL_TRIANGLES)
        

    pyglet.app.run()
