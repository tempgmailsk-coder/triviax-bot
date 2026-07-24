// Turbo Racer Telegram Bot
// Launches an HTML5 racing game as a Telegram Web App and tracks scores.
//
// Setup:
//   1. npm install
//   2. Create a .env file with:
//        BOT_TOKEN=your_bot_token_from_BotFather
//        GAME_URL=https://your-hosted-game-url.com   (must be HTTPS)
//   3. npm start

require('dotenv').config();
const { Telegraf, Markup } = require('telegraf');
const fs = require('fs');
const path = require('path');

const BOT_TOKEN = process.env.BOT_TOKEN;
const GAME_URL = process.env.GAME_URL;

if (!BOT_TOKEN) {
  console.error('Missing BOT_TOKEN in .env');
  process.exit(1);
}
if (!GAME_URL) {
  console.error('Missing GAME_URL in .env (must be an HTTPS URL to your hosted webapp/index.html)');
  process.exit(1);
}

const bot = new Telegraf(BOT_TOKEN);

// --- simple JSON file "database" for the leaderboard ---
const DB_PATH = path.join(__dirname, 'scores.json');

function loadScores() {
  try {
    return JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
  } catch {
    return {};
  }
}

function saveScores(scores) {
  fs.writeFileSync(DB_PATH, JSON.stringify(scores, null, 2));
}

function recordScore(userId, username, score) {
  const scores = loadScores();
  const prev = scores[userId];
  if (!prev || score > prev.best) {
    scores[userId] = { username: username || 'Anonymous', best: score };
    saveScores(scores);
    return true; // new personal best
  }
  return false;
}

function topScores(limit = 10) {
  const scores = loadScores();
  return Object.values(scores)
    .sort((a, b) => b.best - a.best)
    .slice(0, limit);
}

// --- bot commands ---

bot.start((ctx) => {
  ctx.reply(
    `🏁 Welcome to Turbo Racer!\n\nDodge traffic, rack up points, and beat your best score.\n\nTap the button below to start racing.`,
    Markup.inlineKeyboard([
      Markup.button.webApp('🚗 Play Turbo Racer', GAME_URL),
    ])
  );
});

bot.command('play', (ctx) => {
  ctx.reply(
    'Ready to race?',
    Markup.inlineKeyboard([Markup.button.webApp('🚗 Play Turbo Racer', GAME_URL)])
  );
});

bot.command('leaderboard', (ctx) => {
  const top = topScores(10);
  if (top.length === 0) {
    return ctx.reply('No scores yet — be the first to race! Use /play');
  }
  const lines = top.map(
    (s, i) => `${i + 1}. ${s.username} — ${s.best} pts`
  );
  ctx.reply(`🏆 Leaderboard\n\n${lines.join('\n')}`);
});

// This fires when the web app calls Telegram.WebApp.sendData(...)
bot.on('web_app_data', (ctx) => {
  try {
    const data = JSON.parse(ctx.webAppData.data);
    const { score } = data;
    const userId = ctx.from.id;
    const username = ctx.from.username || ctx.from.first_name;

    const isNewBest = recordScore(userId, username, score);

    ctx.reply(
      isNewBest
        ? `🎉 New personal best: ${score} pts!`
        : `Nice run — you scored ${score} pts.`,
      Markup.inlineKeyboard([
        Markup.button.webApp('🔁 Race Again', GAME_URL),
      ])
    );
  } catch (err) {
    console.error('Failed to parse web_app_data:', err);
  }
});

bot.launch().then(() => {
  console.log('Turbo Racer bot is running (polling mode)...');
});

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
