extends RefCounted
# Applies a king look (kinglook.gd dictionary) to the customisable king glb: shows / hides named parts and tints materials.
const KL := preload("res://game/kinglook.gd")
const EYE_FILES := ["brown", "blue", "green", "grey", "hazel"]
static var _eye_tex := {}


static func _tex(i: int) -> Texture2D:
	if not _eye_tex.has(i):
		_eye_tex[i] = load("res://game/models/tex/eye_%s_c.png" % EYE_FILES[i])
	return _eye_tex[i]


static func _meshes(root: Node) -> Array:
	return root.find_children("*", "MeshInstance3D", true, false)


static func _base_name(n: String) -> String:
	var s := n
	while s.length() > 0 and s[s.length() - 1] >= "0" and s[s.length() - 1] <= "9" and false:
		s = s.substr(0, s.length() - 1)
	return s


static func _tint(mi: MeshInstance3D, mat_name: String, fn: Callable) -> void:
	var m: Mesh = mi.mesh
	if m == null:
		return
	for i in m.get_surface_count():
		var mt = mi.get_active_material(i)
		if mt != null and mt is BaseMaterial3D and String(mt.resource_name) == mat_name:
			var d: BaseMaterial3D = mt.duplicate()
			fn.call(d)
			mi.set_surface_override_material(i, d)


static func apply(root: Node, L: Dictionary, team_col: Color, sword_lv := 0, has_shield := true) -> void:
	L = KL.merged(L)
	var helm: int = int(L.helmt)
	var vis := {}
	vis["Helm%d" % helm] = true
	if int(L.crownt) > 0:
		vis["Crown%d" % (int(L.crownt) - 1)] = true
		vis["Gem"] = true
	if helm == 4 and int(L.hair) > 0:
		vis["Hair%d" % int(L.hair)] = true
	if helm != 0:
		match int(L.beard):
			1: vis["BeardStubble"] = true
			2: vis["BeardFull"] = true
			3: vis["BeardBraid"] = true
	vis["Chest%d" % int(L.chest)] = true
	vis["Legs%d" % int(L.legs)] = true
	vis["Boots%d" % int(L.boots)] = true
	if int(L.pauld) < 3:
		vis["Pauld%d" % int(L.pauld)] = true
	if int(L.emblem) > 0:
		vis["Emblem%d" % int(L.emblem)] = true
	if int(L.patch) == 1:
		vis["Patch"] = true
	if int(L.scar) == 1:
		vis["Scar"] = true
	vis["Skin"] = true
	vis["Cape"] = true
	vis["Sword%d" % sword_lv] = true
	if has_shield:
		vis["Shield"] = true
	var arm: Array = KL.ARMOR[int(L.armor)]
	var skin_t: Color = KL.SKIN[int(L.skin)]
	var skin_base: Color = KL.SKIN[0]
	var skin_ratio := Color(skin_t.r / skin_base.r, skin_t.g / skin_base.g, skin_t.b / skin_base.b)
	var hair_c: Color = KL.HAIR[int(L.haircol)]
	var cape_c: Color = team_col if int(L.cape) == 0 else KL.CAPE[int(L.cape)]
	var blade_c: Color = KL.BLADE[int(L.blade)]
	var gem_c: Color = KL.GEM[int(L.gem)]
	for mi in _meshes(root):
		var nm := String(mi.name)
		var known := nm.begins_with("Helm") or nm.begins_with("Crown") or nm.begins_with("Hair") or nm.begins_with("Beard") or nm.begins_with("Chest") or nm.begins_with("Legs") or nm.begins_with("Boots") or nm.begins_with("Pauld") or nm.begins_with("Emblem") or nm in ["Patch", "Scar", "Gem", "Skin", "Cape", "Shield"] or nm.begins_with("Sword")
		if known:
			mi.visible = vis.has(nm)
		if not mi.visible:
			continue
		if nm == "Skin":
			_tint(mi, "body", func(d): d.albedo_color = skin_ratio)
		elif nm.begins_with("Hair") or nm.begins_with("Beard"):
			_tint(mi, "hair", func(d): d.albedo_color = hair_c)
		elif nm == "Cape":
			_tint(mi, "cloth", func(d): d.albedo_color = cape_c)
		elif nm == "Gem":
			_tint(mi, "body", func(d):
				d.albedo_color = gem_c
				d.emission_enabled = true
				d.emission = gem_c
				d.emission_energy_multiplier = 0.9
				d.metallic = 0.3
				d.roughness = 0.2)
		elif nm.begins_with("Sword"):
			var em := 0.7 if (int(L.blade) == 2 or int(L.blade) == 3) else 0.0
			_tint(mi, "steel", func(d):
				d.albedo_color = blade_c
				if em > 0.0:
					d.emission_enabled = true
					d.emission = blade_c
					d.emission_energy_multiplier = em)
		elif nm.begins_with("Helm") or nm.begins_with("Chest") or nm.begins_with("Legs") or nm.begins_with("Boots") or nm == "Pauld0" or nm == "Pauld1":
			_tint(mi, "steel", func(d): d.albedo_color = (arm[0] as Color).lightened(0.12))
	# eye colour: swap the iris texture
	for mi in _meshes(root):
		var m: Mesh = mi.mesh
		if m == null:
			continue
		for i in m.get_surface_count():
			var mt = mi.get_active_material(i)
			if mt != null and mt is BaseMaterial3D and String(mt.resource_name).begins_with("eye_"):
				var d: BaseMaterial3D = mt.duplicate()
				d.albedo_texture = _tex(clampi(int(L.eye), 0, 4))
				mi.set_surface_override_material(i, d)
