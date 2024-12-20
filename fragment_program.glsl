#version 330 core

in vec3 frag_normal;
in vec3 frag_position;
in vec2 frag_texcoord;

out vec4 fragColor;

uniform vec3 light_position1; 
uniform vec3 light_position2; 
uniform vec3 viewPosition; 
uniform vec3 La1;
uniform vec3 Ld1;
uniform vec3 Ls1;
uniform vec3 La2;
uniform vec3 Ld2;
uniform vec3 Ls2;
uniform vec3 Ka;
uniform vec3 Kd;
uniform vec3 Ks;
uniform float shininess;
uniform float constantAttenuation;
uniform float linearAttenuation;
uniform float quadraticAttenuation;

uniform sampler2D samplerTex;

void main()
{
    // ambient
    vec3 ambient1 = Ka * La1;
    vec3 ambient2 = Ka * La2;
    
    // diffuse
    vec3 normalizedNormal = normalize(frag_normal);
    vec3 toLight1 = light_position1 - frag_position;
    vec3 lightDir1 = normalize(toLight1);
    float diff1 = max(dot(normalizedNormal, lightDir1), 0.0);
    vec3 diffuse1 = Kd * Ld1 * diff1;

    vec3 toLight2 = light_position2 - frag_position;
    vec3 lightDir2 = normalize(toLight2);
    float diff2 = max(dot(normalizedNormal, lightDir2), 0.0);
    vec3 diffuse2 = Kd * Ld2 * diff2;
    
    // specular
    vec3 viewDir = normalize(viewPosition - frag_position);
    vec3 reflectDir1 = reflect(-lightDir1, normalizedNormal);  
    float spec1 = pow(max(dot(viewDir, reflectDir1), 0.0), shininess);
    vec3 specular1 = Ks * Ls1 * spec1;

    vec3 reflectDir2 = reflect(-lightDir2, normalizedNormal);  
    float spec2 = pow(max(dot(viewDir, reflectDir2), 0.0), shininess);
    vec3 specular2 = Ks * Ls2 * spec2;

    // attenuation
    float distToLight1 = length(toLight1);
    float attenuation1 = constantAttenuation
        + linearAttenuation * distToLight1
        + quadraticAttenuation * distToLight1 * distToLight1;

    float distToLight2 = length(toLight2);
    float attenuation2 = constantAttenuation
        + linearAttenuation * distToLight2
        + quadraticAttenuation * distToLight2 * distToLight2;
        
    vec4 fragOriginalColor = texture(samplerTex, frag_texcoord);

    vec3 result = (ambient1 + ((diffuse1 + specular1) / attenuation1) + ambient2 + ((diffuse2 + specular2) / attenuation2)) * fragOriginalColor.rgb;
    fragColor = vec4(result, 1.0);
}
