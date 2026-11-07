extends RefCounted
# Online hooks that bring players back: a 7-day login streak with growing rewards (lucky bonus, online bonus),
# three daily quests, a quest-set bonus chest and a rivalry meter on the leaderboard. Saved in user://engage.cfg

const LocS := preload("res://game/loc.gd")
const ProfS := preload("res://game/profile.gd")
const Dev := preload("res://game/device.gd")
const CFG := "user://engage.cfg"

# streak day -> [gold, wood, stone, coins]; day 7 is the big chest
const STREAK := [[80, 40, 20, 0], [120, 60, 30, 0], [170, 80, 40, 20], [230, 110, 55, 0], [300, 140, 70, 40], [400, 180, 90, 0], [800, 300, 150, 150]]

# stat id, target, reward gold, text
const POOL := [
	["caches", 5, 70, "Collect %d treasure caches"],
	["walk", 600, 60, "Travel %d meters on foot"],
	["ride", 800, 70, "Ride your horse %d meters"],
	["recruit", 2, 80, "Recruit %d soldiers"],
	["tax", 2, 90, "Collect tax %d times"],
	["kills", 4, 110, "Defeat %d raiders"],
	["visit", 2, 90, "Greet %d lords in their castles"],
	["houses", 1, 80, "Build %d house outside the castle"],
]

static var loaded := false
static var streak := 0
static var last_claim := -1            # day index of the last claimed login reward
static var q_day := -1
static var q_ids: Array = []
static var q_base := {}
static var q_claimed: Array = []
static var q_bonus := false
static var last_rank := 0
static var rival := ""
static var shown_session := false
static var warned: Dictionary = {}
static var _chk := 0.0
static var _rng := RandomNumberGenerator.new()


static func day_index() -> int:
	var bias := int(Time.get_time_zone_from_system().get("bias", 0))
	return int((Time.get_unix_time_from_system() + bias * 60) / 86400)


static func load_all() -> void:
	if loaded:
		return
	loaded = true
	_rng.randomize()
	var c := ConfigFile.new()
	if c.load(CFG) != OK:
		return
	streak = int(c.get_value("e", "streak", 0))
	last_claim = int(c.get_value("e", "last", -1))
	q_day = int(c.get_value("e", "qday", -1))
	q_ids = Array(c.get_value("e", "qids", []))
	q_base = Dictionary(c.get_value("e", "qbase", {}))
	q_claimed = Array(c.get_value("e", "qclaimed", []))
	q_bonus = bool(c.get_value("e", "qbonus", false))
	last_rank = int(c.get_value("e", "rank", 0))
	rival = String(c.get_value("e", "rival", ""))


static func save() -> void:
	var c := ConfigFile.new()
	c.set_value("e", "streak", streak)
	c.set_value("e", "last", last_claim)
	c.set_value("e", "qday", q_day)
	c.set_value("e", "qids", q_ids)
	c.set_value("e", "qbase", q_base)
	c.set_value("e", "qclaimed", q_claimed)
	c.set_value("e", "qbonus", q_bonus)
	c.set_value("e", "rank", last_rank)
	c.set_value("e", "rival", rival)
	c.save(CFG)


static func T(s: String) -> String:
	return LocS.t(s)


# ------------------------------------------------------------------ login streak
static func can_claim_login() -> bool:
	return last_claim != day_index()


# the streak day this claim would be (1..7), restarting at 1 when a day was missed
static func next_day() -> int:
	var d := day_index()
	if last_claim == d - 1:
		return (streak % 7) + 1
	if last_claim == d:
		return ((streak - 1) % 7) + 1
	return 1


static func online_bonus(world) -> float:
	return 1.5 if world.online_state == "online" else 1.0


static func claim_login(world) -> String:
	if not can_claim_login():
		return ""
	var dn := next_day()
	streak = dn if last_claim != day_index() - 1 else streak + 1
	last_claim = day_index()
	var r: Array = STREAK[dn - 1]
	var mult := online_bonus(world)
	var lucky := _rng.randf() < 0.18
	if lucky:
		mult *= 2.0
	world.res.gold += int(float(r[0]) * mult)
	world.res.wood += int(float(r[1]) * mult)
	world.res.stone += int(float(r[2]) * mult)
	ProfS.load_all()
	ProfS.coins += int(float(r[3]) * mult)
	ProfS.renown += 10 + dn * 4
	ProfS.save()
	save()
	Dev.buzz(70)
	var txt := "%s %d:  +%d %s  +%d %s  +%d %s" % [T("Day"), dn, int(float(r[0]) * mult), T("Gold"), int(float(r[1]) * mult), T("Wood"), int(float(r[2]) * mult), T("Stone")]
	if int(r[3]) > 0:
		txt += "  +%d %s" % [int(float(r[3]) * mult), T("Coins")]
	if lucky:
		txt = T("LUCKY CHEST! Double reward") + "\n" + txt
	elif mult > 1.0:
		txt += "   (" + T("Online bonus") + " x1.5)"
	return txt


# ------------------------------------------------------------------ daily quests
static func ensure_quests(world) -> void:
	var d := day_index()
	if q_day == d and q_ids.size() == 3:
		return
	q_day = d
	var idx: Array = range(POOL.size())
	var r := RandomNumberGenerator.new()
	r.seed = hash(str(d) + _pid(world))
	var pick: Array = []
	while pick.size() < 3:
		var k: int = idx[r.randi() % idx.size()]
		idx.erase(k)
		pick.append(int(k))
	q_ids = pick
	q_base = {}
	for k in pick:
		var sid: String = POOL[k][0]
		q_base[sid] = int(world.life.stats.get(sid, 0))
	q_claimed = []
	q_bonus = false
	save()


static func q_prog(world, k: int) -> int:
	var sid: String = POOL[k][0]
	var cur := int(world.life.stats.get(sid, 0))
	if cur < int(q_base.get(sid, 0)):
		q_base[sid] = cur               # a fresh world: count from here
	return mini(cur - int(q_base.get(sid, 0)), int(POOL[k][1]))


static func q_done(world, k: int) -> bool:
	return q_prog(world, k) >= int(POOL[k][1])


static func claim_quest(world, k: int) -> String:
	if q_claimed.has(k) or not q_done(world, k):
		return ""
	q_claimed.append(k)
	var g := int(float(POOL[k][2]) * online_bonus(world))
	world.res.gold += g
	ProfS.load_all()
	ProfS.renown += 8
	ProfS.save()
	save()
	Dev.buzz(40)
	return "+%d %s" % [g, T("Gold")]


static func all_claimed() -> bool:
	return q_claimed.size() >= 3


static func claim_bonus(world) -> String:
	if q_bonus or not all_claimed():
		return ""
	q_bonus = true
	var m := online_bonus(world)
	world.res.gold += int(200.0 * m)
	world.res.wood += int(100.0 * m)
	world.res.stone += int(60.0 * m)
	ProfS.load_all()
	ProfS.coins += int(60.0 * m)
	ProfS.renown += 25
	ProfS.save()
	save()
	Dev.buzz(90)
	return T("All daily quests done! Bonus chest opened")


static func ready_count(world) -> int:
	if world.life == null:
		return 0
	ensure_quests(world)
	var n := 1 if can_claim_login() else 0
	for k in q_ids:
		if q_done(world, int(k)) and not q_claimed.has(k):
			n += 1
	if all_claimed() and not q_bonus:
		n += 1
	return n


# ------------------------------------------------------------------ rivalry
static func _pid(world) -> String:
	var bk = world._backend()
	return String(bk.player_id) if bk != null else ""


static func my_row(world) -> Dictionary:
	return {"name": T("You"), "level": world.level, "kills": int(world.life.stats.get("kills", 0)), "me": true}


static func ranking(world) -> Array:
	var rows: Array = []
	for e in world.life.board:
		if e is Dictionary and String(e.get("player_id", "")) != _pid(world):
			rows.append({"name": String(e.get("name", "Player")), "level": int(e.get("level", 1)), "kills": int(e.get("kills", 0)), "plat": String(e.get("plat", "")), "pid": String(e.get("player_id", ""))})
	rows.append(my_row(world))
	rows.sort_custom(func(a, b): return a.level > b.level or (a.level == b.level and a.kills > b.kills))
	return rows


static func tick(world, dt: float) -> void:
	load_all()
	_chk -= dt
	if _chk > 0.0 or world.life == null:
		return
	_chk = 4.0
	ensure_quests(world)
	# quest finished -> pop a toast once
	for k in q_ids:
		if q_done(world, int(k)) and not q_claimed.has(k) and not warned.has(k):
			warned[k] = true
			world.hud.toast(T("Quest complete! Open DAILY to claim your reward"), 3.4)
			Dev.buzz(50)
	if world.online_state != "online" or world.life.board.is_empty():
		return
	var rows := ranking(world)
	var me := 0
	for i in rows.size():
		if rows[i].get("me", false):
			me = i + 1
	if last_rank > 0 and me > last_rank and me > 1:
		var who := String(rows[me - 2].name)
		world.hud.toast("%s %s  #%d" % [who, T("overtook you - take your place back!"), me], 4.0)
		Dev.buzz(60)
		rival = who
	elif last_rank > 0 and me < last_rank:
		world.hud.toast("%s #%d" % [T("You climbed the leaderboard to"), me], 3.5)
		Dev.buzz(60)
	if me != last_rank:
		last_rank = me
		save()


# short line: who is just above you, and how far
static func rival_line(world) -> String:
	var rows := ranking(world)
	for i in rows.size():
		if rows[i].get("me", false):
			if i == 0:
				return T("You are #1! Defend your throne.") if rows.size() > 1 else ""
			var r: Dictionary = rows[i - 1]
			var gap: int = int(r.level) - int(world.level)
			return "%s: %s (%s %d)  -  %s" % [T("Next rival"), String(r.name), T("Level"), int(r.level), (T("%d levels ahead") % gap) if gap > 0 else T("same level, more victories")]
	return ""


# ------------------------------------------------------------------ the DAILY window
static func open(world) -> void:
	load_all()
	ensure_quests(world)
	var lines: Array = []
	var dn := next_day()
	var track := ""
	for i in 7:
		var done := (i + 1) < dn or (not can_claim_login() and (i + 1) == dn)
		track += ("[%d]" % (i + 1) if done else "%d" % (i + 1)) + ("   " if i < 6 else "")
	lines.append("%s   %s" % [T("Login streak"), track])
	if world.online_state == "online":
		lines.append(T("Online bonus active: all rewards x1.5"))
	else:
		lines.append(T("Play online for x1.5 rewards"))
	lines.append("")
	lines.append(T("Daily quests"))
	var btns: Array = []
	if can_claim_login():
		var r: Array = STREAK[dn - 1]
		btns.append([T("Claim daily reward") + " (%s %d)" % [T("Day"), dn], "level", func():
			world.hud.toast(claim_login(world), 4.0), true])
	for k in q_ids:
		var kk: int = int(k)
		var txt: String = T(String(POOL[kk][3])) % int(POOL[kk][1])
		var pg := q_prog(world, kk)
		var tag := "  %d / %d" % [pg, int(POOL[kk][1])]
		if q_claimed.has(kk):
			lines.append("[x] " + txt)
		else:
			lines.append("[ ] " + txt + tag)
			if pg >= int(POOL[kk][1]):
				btns.append([T("Claim") + ": " + txt, "heart", func():
					world.hud.toast(claim_quest(world, kk), 2.5), true])
	if all_claimed() and not q_bonus:
		btns.append([T("Open bonus chest"), "level", func():
			world.hud.toast(claim_bonus(world), 3.5), true])
	elif q_bonus:
		lines.append(T("Bonus chest opened - new quests tomorrow"))
	var rl := rival_line(world)
	if rl != "":
		lines.append("")
		lines.append(rl)
	lines.append("")
	lines.append(T("Your device") + ": " + Dev.label() + "   -   " + T("Android and iPhone play together in the same world"))
	btns.append([T("Leaderboard"), "level", func(): world.life.open_board()])
	btns.append([T("Close"), "gear", func(): pass])
	world.hud.dialog(T("Daily rewards and quests"), lines, btns, 1, func(): open(world))
