#version 330
in vec3 position;
in vec3 normal;
in vec3 color;
in vec2 uv;

uniform mat4 transform;
uniform mat4 projection;
uniform mat4 view;

out vec2 frag_texcoord;
out vec3 frag_normal;
out vec3 frag_position;
out vec3 frag_originalcolor;

void main()
{
    frag_position = vec3(transform * vec4(position, 1.0f));
    frag_originalcolor = color;
    frag_normal = mat3(transpose(inverse(transform))) * normal;
    frag_texcoord = uv;
    
    gl_Position = projection * view * vec4(frag_position, 1.0f);
}