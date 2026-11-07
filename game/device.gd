extends RefCounted
# Reads the phone: Android / iPhone / PC, how strong it is, and adapts the game (first-run graphics, vibration).
# Players on both platforms share the same online world (cross-play); the platform tag is shown next to lords.

const SettingsS := preload("res://game/settings.gd")
const CFG := "user://device.cfg"


static func platform() -> String:
	match OS.get_name():
		"Android":
			return "android"
		"iOS":
			return "ios"
	return "pc"


static func label(p := "") -> String:
	var pp := platform() if p == "" else p
	match pp:
		"android":
			return "Android"
		"ios":
			return "iPhone"
	return "PC"


static func is_mobile() -> bool:
	return platform() != "pc"


# 0 = weak, 1 = middle, 2 = strong
static func tier() -> int:
	var cores := OS.get_processor_count()
	var mem := -1
	var mi := OS.get_memory_info()
	if mi.has("physical"):
		mem = int(mi["physical"])
	var gb := float(mem) / 1073741824.0 if mem > 0 else -1.0
	if not is_mobile():
		return 2
	if (gb > 0.0 and gb < 3.2) or cores <= 4:
		return 0
	if (gb >= 5.5 or gb < 0.0) and cores >= 8:
		return 2
	return 1


# New installs only: pick graphics that suit this phone. Players who already chose settings are left alone.
static func auto_setup() -> void:
	var c := ConfigFile.new()
	c.load(CFG)
	if bool(c.get_value("d", "done", false)):
		return
	c.set_value("d", "done", true)
	c.set_value("d", "tier", tier())
	c.save(CFG)
	if is_mobile() and not FileAccess.file_exists(SettingsS.PATH):
		SettingsS.apply_preset([1, 2, 3][tier()])


static func buzz(ms := 40) -> void:
	if is_mobile():
		Input.vibrate_handheld(ms)
