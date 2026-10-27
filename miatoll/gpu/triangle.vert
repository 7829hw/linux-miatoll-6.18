#version 450
// Rotating triangle for vk-shader-probe: positions and colours come from
// gl_VertexIndex, the angle from a push constant.
layout(push_constant) uniform Push { float angle; float aspect; } push;
layout(location = 0) out vec3 colour;

void main()
{
	const vec2 corners[3] = vec2[](vec2(0.0, -0.6), vec2(0.52, 0.3), vec2(-0.52, 0.3));
	const vec3 colours[3] = vec3[](vec3(1.0, 0.0, 0.0), vec3(0.0, 1.0, 0.0), vec3(0.0, 0.0, 1.0));
	vec2 p = corners[gl_VertexIndex];
	float c = cos(push.angle), s = sin(push.angle);
	p = vec2(c * p.x - s * p.y, s * p.x + c * p.y);
	gl_Position = vec4(p.x, p.y * push.aspect, 0.0, 1.0);
	colour = colours[gl_VertexIndex];
}
