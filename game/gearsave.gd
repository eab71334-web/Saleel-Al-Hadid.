extends RefCounted
# Player's sword forge level (0..2) — persisted; used in Open World (online) mode.
const FILE := "user://gear.cfg"
const MAX_LV := 2
static var sword_lv := 0
static var loaded := false

static func load_it() -> void:
	if loaded:
		return
	loaded = true
	var cf := ConfigFile.new()
	if cf.load(FILE) == OK:
		sword_lv = clampi(int(cf.get_value("g", "sword", 0)), 0, MAX_LV)

static func save_it() -> void:
	var cf := ConfigFile.new()
	cf.set_value("g", "sword", sword_lv)
	cf.save(FILE)

static func cost() -> int:
	return 150 * (sword_lv + 1)

static func dmg_mult() -> float:
	return 1.0 + 0.3 * sword_lv
