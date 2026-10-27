#version 450
layout(location = 0) in vec3 colour;
layout(location = 0) out vec4 result;

void main()
{
	result = vec4(colour, 1.0);
}
