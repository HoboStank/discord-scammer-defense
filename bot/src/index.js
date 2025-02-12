const { Client, GatewayIntentBits } = require('discord.js');
const dotenv = require('dotenv');

dotenv.config({ path: './config/.env' });

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

client.once('ready', () => {
  console.log(`Logged in as ${client.user.tag}!`);
});

client.on('guildMemberAdd', async (member) => {
  console.log(`New member joined: ${member.user.tag}`);
  // TODO: Implement detection logic
});

client.on('userUpdate', async (oldUser, newUser) => {
  if (oldUser.avatar !== newUser.avatar || oldUser.username !== newUser.username) {
    console.log(`User updated profile: ${newUser.tag}`);
    // TODO: Implement profile change detection
  }
});

client.login(process.env.DISCORD_TOKEN);