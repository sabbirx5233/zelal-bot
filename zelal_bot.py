import os
import cv2
import json
import re
import numpy as np
import subprocess
import imageio_ffmpeg
import yt_dlp
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Dynamic FFmpeg path detection
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# CONFIGURATION
BOT_TOKEN = "8930717626:AAEemh2JSvoHt6j7vdza6v3R_4tADzb7bso"
CHANNEL_LINK = "https://t.me/ldrzelalx"
CHANNEL_USERNAME = "@ldrzelalx"
ADMIN_ID = 6878235212
WATERMARK_TEXT = "t.me/ldrzelalx"

# USER DATA STORAGE
USERS_FILE = "users.json"
USER_STATES = {}

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.add(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(list(users), f)

def make_progress_bar(percent):
    done = int(percent / 10)
    return "█" * done + "░" * (10 - done)

async def is_user_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        print(f"Subscription Check Error: {e}")
        return True

async def send_force_join_msg(update: Update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Verify / Check Join", callback_data="check_join")]
    ])
    msg_text = "⚠️ *বটটি ব্যবহার করতে আপনাকে প্রথমে আমাদের চ্যানেলে জয়েন করতে হবে!*\n\nনিচের লিংকে গিয়ে জয়েন করে **Verify / Check Join** বাটনে ক্লিক করুন।"
    if update.message:
        await update.message.reply_text(msg_text, parse_mode="Markdown", reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg_text, parse_mode="Markdown")

def combine_audio_high_quality(original_video, processed_video, final_output):
    try:
        cmd = [
            FFMPEG_EXE, '-y', 
            '-i', processed_video, 
            '-i', original_video, 
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'fast',
            '-c:a', 'copy',
            '-map', '0:v:0', 
            '-map', '1:a:0?', 
            final_output
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"Audio Merge Error: {e}")
        return False

def extract_audio_mp3(input_video, output_audio):
    try:
        cmd = [FFMPEG_EXE, '-y', '-i', input_video, '-q:a', '0', '-map', 'a', output_audio]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"Audio Extract Error: {e}")
        return False

# EXPANDED MAIN KEYBOARD WITH REMOVER OPTIONS
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📸 Image to Motion Video"), KeyboardButton("🎬 Video Watermark & Sound")],
        [KeyboardButton("🎵 Extract MP3 Audio"), KeyboardButton("⚡ Change Video Speed (2x)")],
        [KeyboardButton("🧹 Image Watermark Remover"), KeyboardButton("🧼 Video Watermark Remover")],
        [KeyboardButton("📥 Any Social Media Downloader")]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)

    if not await is_user_subscribed(context.bot, user_id):
        await send_force_join_msg(update)
        return

    welcome_text = (
        "✨ *WELCOME TO ALL-IN-ONE MEDIA STUDIO* ✨\n\n"
        "নিচের স্থায়ী বাটনগুলো থেকে আপনার প্রয়োজনীয় সার্ভিসটি বেছে নিন:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_join":
        if await is_user_subscribed(context.bot, user_id):
            await query.message.delete()
            await context.bot.send_message(
                chat_id=user_id, 
                text="✅ *ভেরিফিকেশন সফল হয়েছে!* এখন নিচের বাটন ব্যবহার করে বটটি উপভোগ করুন।", 
                parse_mode="Markdown", 
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await query.message.reply_text("❌ *আপনি এখনো চ্যানেলে জয়েন করেননি!* জয়েন করে আবার চেষ্টা করুন।")

# URL DOWNLOADER FUNCTION
async def download_social_video(update: Update, url: str):
    msg = await update.message.reply_text("🔎 *Processing Video Link...*\n`[████░░░░░░] 40%`", parse_mode="Markdown")
    output_template = f"dl_{update.effective_user.id}.%(ext)s"
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_EXE
    }

    try:
        await msg.edit_text("📥 *Downloading Video from Server...*\n`[████████░░] 80%`", parse_mode="Markdown")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            with open(filename, 'rb') as video:
                await update.message.reply_video(
                    video=video,
                    caption=f"✨ *DOWNLOAD SUCCESSFUL*\n🛡️ *Downloaded via:* `t.me/ldrzelalx`",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                    write_timeout=300
                )
            await msg.delete()
            os.remove(filename)
        else:
            await msg.edit_text("❌ ভিডিওটি ডাউনলোড করা সম্ভব হয়নি!")

    except Exception as e:
        await msg.edit_text(f"❌ *Download Error:* `{str(e)}`", parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    text = update.message.text.strip()

    if not await is_user_subscribed(context.bot, user_id):
        await send_force_join_msg(update)
        return

    url_pattern = re.compile(r'https?://[^\s]+')
    if url_pattern.match(text):
        await download_social_video(update, text)
        return

    if text == "📸 Image to Motion Video":
        USER_STATES[user_id] = "IMAGE"
        await update.message.reply_text("📸 *Photo Mode Enabled!*\nএখন একটি **Photo** পাঠান।", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif text == "🎬 Video Watermark & Sound":
        USER_STATES[user_id] = "VIDEO"
        await update.message.reply_text("🎬 *Video Mode Enabled!*\nএখন একটি **Video** পাঠান।", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif text == "🎵 Extract MP3 Audio":
        USER_STATES[user_id] = "EXTRACT_AUDIO"
        await update.message.reply_text("🎵 *MP3 Extractor Mode!*\nযে ভিডিও থেকে অডিও আলাদা করতে চান সেটি পাঠান।", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif text == "⚡ Change Video Speed (2x)":
        USER_STATES[user_id] = "SPEED_2X"
        await update.message.reply_text("⚡ *Fast Motion Mode Enabled (2x)!*\nযে ভিডিওর স্পিড ২ গুণ বাড়াতে চান সেটি পাঠান।", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif text == "🧹 Image Watermark Remover":
        USER_STATES[user_id] = "REMOVE_IMG_WM"
        await update.message.reply_text("🧹 *Image Watermark Remover Mode!*\nযে ছবির ওয়াটারমার্ক মুছতে চান সেই **Photo** পাঠান।", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif text == "🧼 Video Watermark Remover":
        USER_STATES[user_id] = "REMOVE_VID_WM"
        await update.message.reply_text("🧼 *Video Watermark Remover Mode!*\nযে ভিডিও থেকে লোগো বা ওয়াটারমার্ক রিমুভ করতে চান সেই **Video** পাঠান।", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    elif text == "📥 Any Social Media Downloader":
        USER_STATES[user_id] = "DOWNLOADER"
        await update.message.reply_text(
            "📥 *All-in-One Downloader Ready!*\n\nTikTok, Reels, Shorts, Facebook বা যে কোনো সোশ্যাল মিডিয়ার **Video Link** এখানে পেস্ট করুন।", 
            parse_mode="Markdown", 
            reply_markup=MAIN_KEYBOARD
        )

# ADMIN COMMANDS
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("⚠️ ব্যবহার পদ্ধতি: `/broadcast আপনার মেসেজ`", parse_mode="Markdown")
        return

    message_to_send = " ".join(context.args)
    users = load_users()
    success, failed = 0, 0
    status_msg = await update.message.reply_text(f"🚀 *Broadcasting to {len(users)} users...*", parse_mode="Markdown")

    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 *ANNOUNCEMENT*\n\n{message_to_send}", parse_mode="Markdown")
            success += 1
        except:
            failed += 1

    await status_msg.edit_text(f"✅ *Broadcast Finished!*\n🟢 সফল: `{success}` | 🔴 ফেইল্ড: `{failed}`", parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    users = load_users()
    await update.message.reply_text(f"📊 *Bot Statistics*\n\n👥 মোট রেজিস্টার্ড ইউজার: `{len(users)}`", parse_mode="Markdown")

# PHOTO HANDLER
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    if not await is_user_subscribed(context.bot, user_id):
        await send_force_join_msg(update); return

    state = USER_STATES.get(user_id)

    # IMAGE TO MOTION VIDEO
    if state == "IMAGE":
        msg = await update.message.reply_text(f"📸 *Analyzing Image...*\n`[{make_progress_bar(30)}] 30%`", parse_mode="Markdown")
        input_img, output_video = f"input_{user_id}.jpg", f"motion_{user_id}.mp4"

        try:
            photo_file = await update.message.photo[-1].get_file()
            await photo_file.download_to_drive(input_img, write_timeout=300)
            await msg.edit_text(f"🎬 *Creating Motion Video...*\n`[{make_progress_bar(70)}] 70%`", parse_mode="Markdown")

            base_img = Image.open(input_img).convert("RGBA")
            w, h = base_img.size
            overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            font_size = max(32, int(h / 14))
            try: font = ImageFont.truetype("arialbd.ttf", font_size)
            except: font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
            text_w, text_h = bbox[2] - bbox[1], bbox[3] - bbox[1]
            text_x, text_y = (w - text_w) // 2, int(h * 0.06)

            draw.rectangle([text_x - 12, text_y - 12, text_x + text_w + 12, text_y + text_h + 12], fill=(0, 0, 0, 140))
            draw.text((text_x, text_y), WATERMARK_TEXT, fill=(255, 255, 255, 255), font=font)
            combined = Image.alpha_composite(base_img, overlay).convert("RGB")

            fps, duration = 24, 4
            total_frames = fps * duration
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_video, fourcc, fps, (w, h))

            for frame_num in range(total_frames):
                scale = 1.0 + (0.04 * (frame_num / total_frames))
                new_w, new_h = int(w * scale), int(h * scale)
                resized = combined.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left, top = (new_w - w) // 2, (new_h - h) // 2
                cropped = resized.crop((left, top, left + w, top + h))
                out.write(cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR))

            out.release()
            with open(output_video, 'rb') as video:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=video, caption="🎬 *MOTION VIDEO GENERATED*", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ *Error:* `{str(e)}`", parse_mode="Markdown")
        finally:
            for p in [input_img, output_video]:
                if os.path.exists(p): os.remove(p)

    # TRUE AI-STYLE IMAGE WATERMARK REMOVER (No Blur)
    elif state == "REMOVE_IMG_WM":
        msg = await update.message.reply_text(f"🧹 *Smart Cleaning Watermark from Image...*\n`[{make_progress_bar(50)}] 50%`", parse_mode="Markdown")
        input_img, output_img = f"input_wm_{user_id}.jpg", f"clean_{user_id}.jpg"
        
        try:
            photo_file = await update.message.photo[-1].get_file()
            await photo_file.download_to_drive(input_img, write_timeout=300)

            img = cv2.imread(input_img)
            h, w, _ = img.shape

            # Target standard bottom logo/watermark zone precisely without affecting main photo body
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.rectangle(mask, (0, int(h * 0.90)), (w, h), 255, -1)

            # Fast Marching Method (NS) for sharp seamless background texture reconstruction
            cleaned = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
            cv2.imwrite(output_img, cleaned)

            with open(output_img, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption="✨ *WATERMARK REMOVED SUCCESSFULLY*", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ *Error:* `{str(e)}`", parse_mode="Markdown")
        finally:
            for p in [input_img, output_img]:
                if os.path.exists(p): os.remove(p)
    else:
        await update.message.reply_text("⚠️ আগে **📸 Image to Motion Video** বা **🧹 Image Watermark Remover** বাটন টিপুন!", reply_markup=MAIN_KEYBOARD)

# VIDEO HANDLER
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    if not await is_user_subscribed(context.bot, user_id):
        await send_force_join_msg(update); return

    state = USER_STATES.get(user_id)
    if not state:
        await update.message.reply_text("⚠️ দয়া করে নিচের স্থায়ী কিবোর্ড থেকে একটি অপশন সিলেক্ট করুন!", reply_markup=MAIN_KEYBOARD)
        return

    input_video = f"input_{user_id}.mp4"
    msg = await update.message.reply_text(f"📥 *Downloading Video...*\n`[{make_progress_bar(20)}] 20%`", parse_mode="Markdown")

    try:
        video_file = await update.message.video.get_file()
        await video_file.download_to_drive(input_video, write_timeout=300)

        # 1. EXTRACT AUDIO FEATURE
        if state == "EXTRACT_AUDIO":
            output_audio = f"audio_{user_id}.mp3"
            await msg.edit_text(f"🎵 *Extracting MP3 Audio...*\n`[{make_progress_bar(70)}] 70%`", parse_mode="Markdown")
            if extract_audio_mp3(input_video, output_audio):
                with open(output_audio, 'rb') as audio:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio, caption="🎵 *Extracted Audio MP3*", reply_markup=MAIN_KEYBOARD)
                await msg.delete()
            else:
                await msg.edit_text("❌ এই ভিডিওতে কোনো সাউন্ড ট্র্যাক পাওয়া যায়নি!")
            if os.path.exists(output_audio): os.remove(output_audio)

        # 2. ADD WATERMARK & SOUND
        elif state == "VIDEO":
            temp_video, final_video = f"temp_{user_id}.mp4", f"final_{user_id}.mp4"
            await msg.edit_text(f"⚡ *Applying Watermark...*\n`[{make_progress_bar(50)}] 50%`", parse_mode="Markdown")

            cap = cv2.VideoCapture(input_video)
            w, h = int(cap.get(3)), int(cap.get(4))
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            out = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

            font_scale = max(1.1, w / 450.0)
            thickness = max(3, int(font_scale * 2.5))
            (text_w, text_h), baseline = cv2.getTextSize(WATERMARK_TEXT, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            text_x, text_y = (w - text_w) // 2, int(h * 0.10)

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                overlay = frame.copy()
                cv2.rectangle(overlay, (text_x - 15, text_y - text_h - 12), (text_x + text_w + 15, text_y + baseline + 12), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
                cv2.putText(frame, WATERMARK_TEXT, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
                cv2.putText(frame, WATERMARK_TEXT, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
                out.write(frame)

            cap.release(); out.release()
            await msg.edit_text(f"🎵 *Finalizing Audio & Video...*\n`[{make_progress_bar(80)}] 80%`", parse_mode="Markdown")
            has_audio = combine_audio_high_quality(input_video, temp_video, final_video)
            send_path = final_video if (has_audio and os.path.exists(final_video)) else temp_video

            with open(send_path, 'rb') as video:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=video, caption="✨ *PROCESSED HD VIDEO*", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
            await msg.delete()
            for p in [temp_video, final_video]:
                if os.path.exists(p): os.remove(p)

        # 3. SPEED CONTROLLER (2X FAST)
        elif state == "SPEED_2X":
            speed_video = f"speed_{user_id}.mp4"
            await msg.edit_text(f"⚡ *Increasing Speed (2x)...*\n`[{make_progress_bar(70)}] 70%`", parse_mode="Markdown")
            cmd = [FFMPEG_EXE, '-y', '-i', input_video, '-filter_complex', '[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]', '-map', '[v]', '-map', '[a]', speed_video]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(speed_video):
                with open(speed_video, 'rb') as video:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=video, caption="⚡ *2X Fast Speed Video*", reply_markup=MAIN_KEYBOARD)
                os.remove(speed_video)
                await msg.delete()
            else:
                await msg.edit_text("❌ স্পিড পরিবর্তন করার সময় সমস্যা হয়েছে!")

        # 4. FIXED VIDEO WATERMARK REMOVER (CROP/SUBTITLE OVERLAY COMPATIBLE)
        elif state == "REMOVE_VID_WM":
            clean_vid = f"clean_vid_{user_id}.mp4"
            await msg.edit_text(f"🧼 *Removing Watermark from Video...*\n`[{make_progress_bar(60)}] 60%`", parse_mode="Markdown")
            
            # Safe crop/filter alternative that avoids resolution mismatch crash
            cmd = [
                FFMPEG_EXE, '-y',
                '-i', input_video,
                '-vf', "delogo=x=10:y=H-50:w=150:h=40",
                '-c:a', 'copy',
                clean_vid
            ]
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if os.path.exists(clean_vid) and os.path.getsize(clean_vid) > 0:
                with open(clean_vid, 'rb') as video:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=video, caption="🧼 *VIDEO WATERMARK REMOVED SUCCESSFULLY*", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
                os.remove(clean_vid)
                await msg.delete()
            else:
                # Fallback backup method if default logo coordinate shifts
                fallback_cmd = [FFMPEG_EXE, '-y', '-i', input_video, '-c:v', 'libx264', '-crf', '23', '-c:a', 'copy', clean_vid]
                subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(clean_vid):
                    with open(clean_vid, 'rb') as video:
                        await context.bot.send_video(chat_id=update.effective_chat.id, video=video, caption="🧼 *VIDEO PROCESSED*", reply_markup=MAIN_KEYBOARD)
                    os.remove(clean_vid)
                    await msg.delete()
                else:
                    await msg.edit_text("❌ ওয়াটারমার্ক রিমুভ করতে সমস্যা হয়েছে!")

    except Exception as e:
        await msg.edit_text(f"❌ *Error:* `{str(e)}`", parse_mode="Markdown")
    finally:
        if os.path.exists(input_video): os.remove(input_video)

def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .read_timeout(300)
        .write_timeout(300)
        .connect_timeout(300)
        .pool_timeout(300)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    print("🚀 Bot is Running with Updated Fixes...")
    app.run_polling()

if __name__ == '__main__':
    main()