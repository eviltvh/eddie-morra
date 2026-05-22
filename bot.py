"""
bot.py — Eddie Morra Bot
Bot de Telegram para gestionar tu stack nootrópico.

Instalar: pip install python-telegram-bot apscheduler matplotlib numpy
Correr:   python bot.py  (con BOT_TOKEN en variables de entorno)
"""
import logging
import os
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from substances import SUBSTANCES, SUBSTANCE_MAP, SLOT_META, WASHOUT_SUSPEND
import chart as ch

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("EddieMorra")

BOT_TOKEN = os.getenv("BOT_TOKEN", "AQUI_VA_TU_TOKEN")


# ── Helpers ──────────────────────────────────────────────────────────────────

def is_rest_day() -> bool:
    return date.today().weekday() >= 5


def streak_badge(n: int) -> str:
    if n == 0:   return "😴"
    if n < 3:    return "🌱"
    if n < 7:    return "🔥"
    if n < 14:   return "💪"
    if n < 30:   return "⚡"
    if n < 60:   return "🧠"
    return "🏆"


def get_active_subs_for_slot(chat_id: int, slot: str, phase: str) -> list:
    available = db.get_available_substances(chat_id)
    result = []
    for s in SUBSTANCES:
        if s["slot"] != slot:
            continue
        if s["id"] not in available:
            continue
        if phase == "washout" and s["id"] in WASHOUT_SUSPEND:
            continue
        if is_rest_day() and slot == "boost":
            continue
        result.append(s)
    return result


def build_reminder_text(chat_id: int, slot: str, phase: str, streak: int) -> str | None:
    subs = get_active_subs_for_slot(chat_id, slot, phase)
    if not subs:
        return None

    meta = SLOT_META[slot]
    phase_labels = {
        "loading":     "⬆️ Fase CARGA",
        "maintenance": "✅ Fase MANTENIMIENTO",
        "washout":     "🔄 Fase WASHOUT",
    }
    greet = {
        "morning": "Buenos días, cerebro",
        "boost":   "Hora del boost cognitivo",
        "night":   "Modo recuperación activado",
    }
    rest_tag = "  🏖️ _[Drug Holiday — solo base]_" if is_rest_day() and slot != "night" else ""

    lines = [
        f"{meta['emoji']} *{greet[slot]}*{rest_tag}",
        f"_{phase_labels.get(phase, '')}_",
        "",
        "Es hora de tu stack:",
        "",
    ]
    for s in subs:
        cy = " ♻️" if s["cyclable"] else ""
        lines.append(f"  • *{s['name']}* `{s['dose']}`{cy}")
        lines.append(f"    _{s['note']}_")

    lines += ["", f"🔥 Racha: *{streak} días* {streak_badge(streak)}"]

    if streak > 0 and streak % 7 == 0:
        lines.append(f"🏆 *¡{streak // 7} semana(s) completa(s)!*")

    return "\n".join(lines)


def dose_keyboard(slot: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ La tomé", callback_data=f"confirm:{slot}"),
        InlineKeyboardButton("⏭ Saltar",  callback_data=f"skip:{slot}"),
    ]])


async def send_reminder(app: Application, chat_id: int, slot: str):
    cycle  = db.get_cycle(chat_id)
    streak = db.get_streak(chat_id)
    phase  = cycle["phase"] if cycle else "maintenance"
    cur    = streak["current_streak"] if streak else 0

    if is_rest_day() and slot == "morning":
        await app.bot.send_message(
            chat_id=chat_id,
            text=(
                "🏖️ *Drug Holiday — Fin de semana*\n\n"
                "Hoy solo toma tu *base neuroprotectora*:\n"
                "  • Omega-3 DHA/EPA\n"
                "  • Vitamina D3 + K2\n"
                "  • Magnesio L-Treonato\n\n"
                f"🔥 Racha: *{cur} días* {streak_badge(cur)}"
            ),
            parse_mode="Markdown",
            reply_markup=dose_keyboard("morning")
        )
        return

    text = build_reminder_text(chat_id, slot, phase, cur)
    if text:
        await app.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=dose_keyboard(slot)
        )


async def schedule_user(app: Application, scheduler: AsyncIOScheduler, chat_id: int):
    s = db.get_settings(chat_id)
    if not s:
        return
    for jid in [f"m_{chat_id}", f"b_{chat_id}", f"n_{chat_id}"]:
        if scheduler.get_job(jid):
            scheduler.remove_job(jid)

    scheduler.add_job(send_reminder, "cron", args=[app, chat_id, "morning"],
                      hour=s["morning_hour"], minute=s["morning_min"],
                      id=f"m_{chat_id}", replace_existing=True)
    scheduler.add_job(send_reminder, "cron", args=[app, chat_id, "boost"],
                      hour=s["boost_hour"], minute=s["boost_min"],
                      id=f"b_{chat_id}", replace_existing=True)
    scheduler.add_job(send_reminder, "cron", args=[app, chat_id, "night"],
                      hour=s["night_hour"], minute=s["night_min"],
                      id=f"n_{chat_id}", replace_existing=True)


# ── /start ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id

    db.upsert_user(chat_id, user.username or user.first_name)
    db.create_cycle(chat_id)

    scheduler: AsyncIOScheduler = ctx.bot_data["scheduler"]
    app: Application            = ctx.bot_data["app"]
    await schedule_user(app, scheduler, chat_id)

    await update.message.reply_text(
        "🧠 *Eddie Morra Bot*\n\n"
        "Protocolo nootrópico iniciado.\n"
        "Ciclo TDAH: *8 semanas ON → 2 semanas WASHOUT*\n"
        "Drug Holiday: *Sábado y Domingo*\n\n"
        "*Comandos:*\n"
        "  /stack — Configurar tu stack\n"
        "  /grafica — Ver gráfica polar cognitiva\n"
        "  /ciclo — Estado del ciclo\n"
        "  /racha — Tus estadísticas\n"
        "  /hoy — Resumen del día\n"
        "  /tomar — Confirmar dosis manualmente\n"
        "  /horario 07:30 11:00 21:30 — Cambiar horarios\n"
        "  /pausar — Pausar recordatorios",
        parse_mode="Markdown"
    )


# ── /stack ───────────────────────────────────────────────────────────────────

async def cmd_stack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id   = update.effective_chat.id
    available = db.get_available_substances(chat_id)

    lines = ["🧪 *Tu Stack — toca para activar/desactivar*\n"]
    rows  = []

    for slot in ["morning", "boost", "night"]:
        meta = SLOT_META[slot]
        slot_subs = [s for s in SUBSTANCES if s["slot"] == slot]
        lines.append(f"*{meta['emoji']} {meta['label']}*")

        slot_row = []
        for s in slot_subs:
            is_on  = s["id"] in available
            emoji  = "✅" if is_on else "❌"
            cy_tag = " ♻️" if s["cyclable"] else ""
            lines.append(
                f"  {emoji} *{s['name']}* `{s['dose']}`{cy_tag}\n"
                f"     _{s['note']}_"
            )
            label = f"{'✅' if is_on else '❌'} {s['name']}"
            slot_row.append(
                InlineKeyboardButton(label, callback_data=f"tog:{s['id']}")
            )
            # 2 botones por fila max
            if len(slot_row) == 2:
                rows.append(slot_row)
                slot_row = []
        if slot_row:
            rows.append(slot_row)
        lines.append("")

    lines.append("♻️ = ciclable  |  ❌ = no disponible")
    rows.append([InlineKeyboardButton("📊 Ver gráfica", callback_data="show_chart")])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows)
    )


# ── /grafica ─────────────────────────────────────────────────────────────────

async def cmd_grafica(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id   = update.effective_chat.id
    available = db.get_available_substances(chat_id)
    cycle     = db.get_cycle(chat_id)
    phase     = cycle["phase"] if cycle else "maintenance"
    user      = update.effective_user

    await update.message.reply_text("_Generando tu perfil cognitivo..._", parse_mode="Markdown")

    img_bytes = ch.generate_radar(available, phase, user.first_name)
    missing   = ch.generate_missing_report(available)

    await update.message.reply_photo(
        photo=img_bytes,
        caption=missing,
        parse_mode="Markdown"
    )


# ── /ciclo ───────────────────────────────────────────────────────────────────

async def cmd_ciclo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cycle   = db.get_cycle(chat_id)

    if not cycle:
        await update.message.reply_text("No tienes ciclo activo. Usa /start.")
        return

    from datetime import date as _date
    remaining = (_date.fromisoformat(cycle["phase_end_date"]) - _date.today()).days
    phase_meta = {
        "loading":     ("⬆️ CARGA",        "Semanas 1–2: todas las sustancias activas"),
        "maintenance": ("✅ MANTENIMIENTO", "Semanas 3–8: régimen estándar óptimo"),
        "washout":     ("🔄 WASHOUT",       "Solo base — limpieza de receptores"),
    }
    ph_label, ph_desc = phase_meta.get(cycle["phase"], ("❓", ""))

    text = (
        f"*Ciclo Eddie Morra*\n\n"
        f"Fase actual: *{ph_label}*\n"
        f"_{ph_desc}_\n\n"
        f"📅 Semana {cycle['week_in_phase']} · Día {cycle['cycle_day']}\n"
        f"⏳ {remaining} días restantes en esta fase\n"
        f"📊 ON: {cycle['on_weeks']} sem  ·  OFF: {cycle['off_weeks']} sem\n\n"
    )
    if cycle["phase"] == "washout":
        text += "💊 Durante washout solo se activan sustancias base\n_(Omega-3, D3+K2, Magnesio, Glicina, Ashwagandha)_"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬆️ Ir a CARGA",        callback_data="phase:loading"),
        InlineKeyboardButton("✅ Ir a MAINT.",        callback_data="phase:maintenance"),
        InlineKeyboardButton("🔄 Ir a WASHOUT",      callback_data="phase:washout"),
    ]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


# ── /racha ───────────────────────────────────────────────────────────────────

async def cmd_racha(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    streak  = db.get_streak(chat_id)
    if not streak:
        await update.message.reply_text("Usa /start primero.")
        return

    cur     = streak["current_streak"]
    longest = streak["longest_streak"]
    total   = streak["total_doses"]
    badge   = streak_badge(cur)

    milestones = [3, 7, 14, 30, 60, 90]
    nxt = next((m for m in milestones if m > cur), 90)
    filled = int((cur / nxt) * 12)
    bar    = "█" * filled + "░" * (12 - filled)

    motivational = {
        0:  "_Empieza hoy. El primer día es el más importante._",
        3:  "_3 días seguidos. La Bacopa empieza a trabajar._",
        7:  "_¡Una semana! Los niveles séricos se están estableciendo._",
        14: "_2 semanas. Lion's Mane estimulando NGF activamente._",
        30: "_Un mes. Neuroprotección en régimen óptimo. 🧠_",
        60: "_60 días. Plasticidad sináptica en su máximo. Nivel élite._",
    }
    msg_key = max((k for k in motivational if k <= cur), default=0)

    text = (
        f"{badge} *Tus estadísticas*\n\n"
        f"🔥 Racha actual: *{cur} días*\n"
        f"🏆 Mejor racha:  *{longest} días*\n"
        f"💊 Total dosis:  *{total}*\n\n"
        f"Próximo hito: *{nxt} días*\n"
        f"`{bar}` {cur}/{nxt}\n\n"
        f"{motivational[msg_key]}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── /hoy ─────────────────────────────────────────────────────────────────────

async def cmd_hoy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    doses   = db.get_today_doses(chat_id)
    streak  = db.get_streak(chat_id)
    today   = date.today().strftime("%a %d/%m/%Y")
    cur     = streak["current_streak"] if streak else 0

    dose_map  = {d["dose_slot"]: d for d in doses}
    slot_icon = {"morning": "🌅 Mañana", "boost": "⚡ Boost", "night": "🌙 Noche"}

    lines  = [f"📋 *Resumen de hoy* — {today}"]
    if is_rest_day():
        lines.append("_🏖️ Drug Holiday (Sáb/Dom)_")
    lines.append("")

    confirmed = 0
    skipped   = 0
    pending   = []
    for slot in ["morning", "boost", "night"]:
        d = dose_map.get(slot)
        if d:
            icon = "✅" if d["confirmed"] else "⏭"
            if d["confirmed"]: confirmed += 1
            else:              skipped   += 1
        else:
            icon = "⬜"
            pending.append(slot)
        lines.append(f"{icon} {slot_icon[slot]}")

    lines += [
        "",
        f"🔥 Racha: *{cur} días* {streak_badge(cur)}",
        f"✅ {confirmed}/3  ⏭ {skipped}/3",
    ]

    kb_row = [
        InlineKeyboardButton(
            {"morning": "🌅", "boost": "⚡", "night": "🌙"}[s],
            callback_data=f"confirm:{s}"
        ) for s in pending
    ]
    kb = InlineKeyboardMarkup([kb_row]) if kb_row else None

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kb
    )


# ── /tomar ───────────────────────────────────────────────────────────────────

async def cmd_tomar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌅 Mañana", callback_data="confirm:morning"),
        InlineKeyboardButton("⚡ Boost",  callback_data="confirm:boost"),
        InlineKeyboardButton("🌙 Noche",  callback_data="confirm:night"),
    ]])
    await update.message.reply_text("¿Qué dosis confirmas?", reply_markup=kb)


# ── /horario ─────────────────────────────────────────────────────────────────

async def cmd_horario(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args    = ctx.args
    if len(args) != 3:
        await update.message.reply_text(
            "Uso: `/horario 07:30 11:00 21:30`\n_(mañana boost noche)_",
            parse_mode="Markdown"
        )
        return
    try:
        times = [tuple(map(int, a.split(":"))) for a in args]
        assert all(0 <= h <= 23 and 0 <= m <= 59 for h, m in times)
    except Exception:
        await update.message.reply_text("Formato inválido. Usa HH:MM en 24h.")
        return

    keys = [("morning_hour", "morning_min"), ("boost_hour", "boost_min"), ("night_hour", "night_min")]
    for (hk, mk), (h, m) in zip(keys, times):
        db.update_setting(chat_id, hk, h)
        db.update_setting(chat_id, mk, m)

    scheduler: AsyncIOScheduler = ctx.bot_data["scheduler"]
    app: Application            = ctx.bot_data["app"]
    await schedule_user(app, scheduler, chat_id)

    await update.message.reply_text(
        f"⏰ Horarios guardados:\n"
        f"  🌅 Mañana: `{args[0]}`\n"
        f"  ⚡ Boost:   `{args[1]}`\n"
        f"  🌙 Noche:   `{args[2]}`",
        parse_mode="Markdown"
    )


# ── /pausar ──────────────────────────────────────────────────────────────────

async def cmd_pausar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.update_setting(chat_id, "morning_hour", 3)
    await update.message.reply_text(
        "⏸ Recordatorios pausados.\nUsa /start para reactivarlos."
    )


# ── Callbacks ─────────────────────────────────────────────────────────────────

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    data    = query.data
    await query.answer()

    # Toggle de sustancia
    if data.startswith("tog:"):
        sub_id  = data[4:]
        new_state = db.toggle_substance(chat_id, sub_id)
        sub = SUBSTANCE_MAP.get(sub_id)
        name = sub["name"] if sub else sub_id
        status = "activada ✅" if new_state else "desactivada ❌"
        await query.answer(f"{name} {status}", show_alert=False)
        # Refrescar el mensaje de stack
        await _refresh_stack_message(query, chat_id)
        return

    # Mostrar gráfica desde botón
    if data == "show_chart":
        available = db.get_available_substances(chat_id)
        cycle     = db.get_cycle(chat_id)
        phase     = cycle["phase"] if cycle else "maintenance"
        img_bytes = ch.generate_radar(available, phase)
        missing   = ch.generate_missing_report(available)
        await query.message.reply_photo(
            photo=img_bytes, caption=missing, parse_mode="Markdown"
        )
        return

    # Confirmar dosis
    if data.startswith("confirm:"):
        slot   = data.split(":")[1]
        db.log_dose(chat_id, slot, confirmed=True)
        streak = db.update_streak(chat_id, confirmed=True)
        cur    = streak["current_streak"]
        labels = {"morning": "mañana", "boost": "boost", "night": "noche"}
        msg    = (
            f"✅ *Dosis de {labels.get(slot, slot)} confirmada*\n\n"
            f"🔥 Racha: *{cur} días* {streak_badge(cur)}"
        )
        if cur == 7:   msg += "\n\n🏆 ¡Primera semana completa! Bacopa acumulándose."
        if cur == 30:  msg += "\n\n🧠 ¡30 días! Neuroprotección en nivel óptimo."
        await query.edit_message_text(msg, parse_mode="Markdown")
        return

    if data.startswith("skip:"):
        slot = data.split(":")[1]
        db.log_dose(chat_id, slot, confirmed=False)
        db.update_streak(chat_id, confirmed=False)
        await query.edit_message_text(
            "⏭ *Dosis saltada.*\n"
            "_La Bacopa necesita consistencia — intenta no saltar seguido._",
            parse_mode="Markdown"
        )
        return

    # Control de fase
    if data.startswith("phase:"):
        phase = data[6:]
        db.force_phase(chat_id, phase)
        phase_names = {"loading": "CARGA ⬆️", "maintenance": "MANTENIMIENTO ✅", "washout": "WASHOUT 🔄"}
        await query.edit_message_text(
            f"✅ Fase cambiada a *{phase_names.get(phase, phase)}*.",
            parse_mode="Markdown"
        )
        return


async def _refresh_stack_message(query, chat_id: int):
    """Re-renderiza el mensaje /stack con el nuevo estado."""
    available = db.get_available_substances(chat_id)
    lines = ["🧪 *Tu Stack — toca para activar/desactivar*\n"]
    rows  = []

    for slot in ["morning", "boost", "night"]:
        meta      = SLOT_META[slot]
        slot_subs = [s for s in SUBSTANCES if s["slot"] == slot]
        lines.append(f"*{meta['emoji']} {meta['label']}*")
        slot_row  = []

        for s in slot_subs:
            is_on  = s["id"] in available
            emoji  = "✅" if is_on else "❌"
            cy_tag = " ♻️" if s["cyclable"] else ""
            lines.append(
                f"  {emoji} *{s['name']}* `{s['dose']}`{cy_tag}\n"
                f"     _{s['note']}_"
            )
            slot_row.append(
                InlineKeyboardButton(
                    f"{'✅' if is_on else '❌'} {s['name']}",
                    callback_data=f"tog:{s['id']}"
                )
            )
            if len(slot_row) == 2:
                rows.append(slot_row)
                slot_row = []
        if slot_row:
            rows.append(slot_row)
        lines.append("")

    lines.append("♻️ = ciclable  |  ❌ = no disponible")
    rows.append([InlineKeyboardButton("📊 Ver gráfica", callback_data="show_chart")])

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows)
    )


# ── Daily tick ───────────────────────────────────────────────────────────────

async def daily_tick(app: Application):
    users = db.get_all_active_users()
    for u in users:
        db.advance_cycle(u["chat_id"])
    log.info(f"Daily tick: {len(users)} usuarios")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    db.init_db()

    app       = Application.builder().token(BOT_TOKEN).build()
    scheduler = AsyncIOScheduler()

    app.bot_data["scheduler"] = scheduler
    app.bot_data["app"]       = app

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("stack",   cmd_stack))
    app.add_handler(CommandHandler("grafica", cmd_grafica))
    app.add_handler(CommandHandler("ciclo",   cmd_ciclo))
    app.add_handler(CommandHandler("racha",   cmd_racha))
    app.add_handler(CommandHandler("hoy",     cmd_hoy))
    app.add_handler(CommandHandler("tomar",   cmd_tomar))
    app.add_handler(CommandHandler("horario", cmd_horario))
    app.add_handler(CommandHandler("pausar",  cmd_pausar))
    app.add_handler(CallbackQueryHandler(on_callback))

    scheduler.add_job(daily_tick, "cron", args=[app], hour=0, minute=1)

    async def post_init(application: Application):
        scheduler.start()
        users = db.get_all_active_users()
        for u in users:
            await schedule_user(application, scheduler, u["chat_id"])
        log.info(f"Startup: {len(users)} usuarios programados")

    app.post_init = post_init

    log.info("🧠 Eddie Morra Bot iniciado.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
