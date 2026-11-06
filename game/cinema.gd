extends RefCounted
# Cinematic look: overcast grade, fog, rain, vignette, over-the-shoulder camera with walking bob.
const Settings := preload("res://game/settings.gd")

static func on() -> bool:
	return Settings.s_fx >= 1


static func grade(env: Environment, sun: DirectionalLight3D, sm: ProceduralSkyMaterial) -> void:
	if not on():
		return
	sm.sky_top_color = Color(0.30, 0.34, 0.40)
	sm.sky_horizon_color = Color(0.58, 0.62, 0.67)
	sm.ground_horizon_color = Color(0.38, 0.40, 0.41)
	sm.ground_bottom_color = Color(0.15, 0.16, 0.17)
	env.fog_light_color = Color(0.50, 0.55, 0.61)
	env.fog_density = 0.0055
	env.ambient_light_energy = 0.62
	env.adjustment_saturation = 0.62
	env.adjustment_contrast = 1.18
	sun.light_energy = 0.75
	sun.light_color = Color(0.86, 0.89, 0.96)


static func overlay(parent: Node) -> void:
	if not on():
		return
	var cl := CanvasLayer.new()
	cl.layer = 3
	var r := ColorRect.new()
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sh := Shader.new()
	sh.code = "shader_type canvas_item;\nvoid fragment(){ vec2 uv = UV - 0.5; float v = smoothstep(0.30, 0.85, length(uv * vec2(1.0, 1.15))); COLOR = vec4(0.0, 0.0, 0.02, v * 0.62); }"
	var m := ShaderMaterial.new()
	m.shader = sh
	r.material = m
	cl.add_child(r)
	parent.add_child.call_deferred(cl)


static func rain(parent: Node) -> Node3D:
	if not on() or Settings.s_fx < 1 or Settings.quality < 1:
		return null
	var p := CPUParticles3D.new()
	p.amount = 260 if Settings.quality == 1 else 520
	p.lifetime = 0.9
	p.preprocess = 1.0
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(14, 0.5, 14)
	p.direction = Vector3(0.12, -1, 0.05)
	p.spread = 2.0
	p.initial_velocity_min = 22.0
	p.initial_velocity_max = 26.0
	p.gravity = Vector3(0, -6, 0)
	var q := BoxMesh.new()
	q.size = Vector3(0.012, 0.55, 0.012)
	var mt := StandardMaterial3D.new()
	mt.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mt.albedo_color = Color(0.78, 0.84, 0.92, 0.35)
	mt.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	q.material = mt
	p.mesh = q
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child.call_deferred(p)
	return p


# over-the-shoulder offset (right of the camera) and walking bob
static func shoulder(yaw: float) -> Vector3:
	return Vector3(-cos(yaw), 0.0, sin(yaw)) * 0.8


static func bob(t: float, speed: float) -> float:
	if speed < 0.4:
		return 0.012 * sin(t * 1.3)
	return 0.04 * sin(t * clampf(speed, 1.0, 6.0) * 1.9)
