# Phase 2 Testing Guide

## Prerequisites
1. Bot is running and connected to Discord
2. PostgreSQL database is running
3. Bot has proper permissions in your server
4. You have administrator permissions in the test server

## 1. Server Configuration Testing

### Basic Configuration
```
!dsd config view
```
Expected: Shows current server configuration

### Channel Setup
```
!dsd config setchannel alert #alerts
!dsd config setchannel log #mod-logs
```
Expected: Bot confirms channel settings

Common Issues:
- Error: "Missing Permissions"
  - Solution: Ensure bot has "View Channel" and "Send Messages" permissions in the specified channels
  - Check: Server Settings > Roles > DSD Bot > Channel Permissions

### Auto-Moderation Settings
```
!dsd config setaction warn 0.7
!dsd config setaction kick 0.85
!dsd config setaction ban 0.95
```
Expected: Bot confirms threshold settings

Common Issues:
- Values not saving
  - Solution: Check database connection
  - Run: `!dsd config view` to verify changes

### Role Configuration
```
!dsd config setrole trusted @Moderator
!dsd config setrole immune @Admin
```
Expected: Bot confirms role settings

Common Issues:
- Role not found
  - Solution: Mention the role directly (@Role) instead of typing the name
  - Check: Role hierarchy (bot's role should be above managed roles)

## 2. Detection System Testing

### Basic Scan Test
1. Create a test account
2. Copy server owner's profile picture
3. Set similar username
4. Join server
```
!dsd scan @TestUser
```
Expected: 
- High risk score
- Detection factors listed
- Alert in configured channel

Common Issues:
- No detection
  - Check: Profile similarity thresholds in config
  - Solution: Lower detection threshold temporarily for testing

### Auto-Moderation Test
1. Create another test account
2. Make it very similar to server owner
3. Join server

Expected:
- Automatic detection
- Action taken based on risk level
- Log entry created
- Alert sent to configured channel

Common Issues:
- Actions not triggering
  - Check: Bot permissions
  - Check: Role hierarchy
  - Solution: Ensure bot role is high enough to manage members

## 3. Logging System Testing

### Action Logging
1. Perform moderation actions:
```
!dsd warn @User Test warning
!dsd kick @User Test kick
!dsd ban @User Test ban
```
Expected:
- Action logged in database
- Log message in configured channel
- Detailed embed with action info

Common Issues:
- Logs not appearing
  - Check: Log channel permissions
  - Check: Database connection
  - Solution: Use `!dsd config view` to verify log channel

### User History
```
!dsd history @User
```
Expected: Shows user's moderation history

Common Issues:
- History not showing
  - Check: Database queries
  - Solution: Verify actions are being logged properly

## 4. Database Verification

1. Access pgAdmin:
   - URL: http://localhost:5050
   - Login: admin@dsd.com
   - Password: admin123

2. Check Tables:
   - scammer_profiles
   - detection_events
   - mod_logs
   - server_configs

Common Issues:
- Can't connect to pgAdmin
  - Solution: Restart Docker containers
  ```bash
  docker-compose down
  docker-compose up -d
  ```

- Tables missing
  - Solution: Re-run SQL setup scripts
  - Check database connection string

## 5. Common Global Issues

### Bot Not Responding
1. Check bot status
2. Verify token in .env
3. Check Discord connection
4. Restart bot:
```bash
cd bot
python src/bot.py
```

### Database Connection Issues
1. Check PostgreSQL container:
```bash
docker ps
```
2. Check logs:
```bash
docker-compose logs db
```
3. Verify connection string in .env

### Permission Issues
1. Check bot role hierarchy
2. Required Permissions:
   - Manage Messages
   - Kick Members
   - Ban Members
   - View Channels
   - Send Messages
   - Embed Links

### Command Not Found
1. Check command prefix (!dsd)
2. Verify cogs are loaded
3. Check bot logs for loading errors

## Testing Checklist

### Basic Setup
- [ ] Bot connects successfully
- [ ] Database accessible
- [ ] Permissions configured

### Configuration
- [ ] Can view config
- [ ] Can set channels
- [ ] Can configure actions
- [ ] Can manage roles

### Detection
- [ ] Scans work manually
- [ ] Auto-detection works
- [ ] Risk levels accurate
- [ ] Actions trigger correctly

### Logging
- [ ] Actions logged to database
- [ ] Channel logs working
- [ ] History retrievable
- [ ] Audit trail complete

## Troubleshooting Tools

### Bot Status
```
!dsd status
```
Shows:
- Connected servers
- Loaded modules
- Current configuration

### Database Check
```
!dsd dbcheck
```
Verifies:
- Connection status
- Table existence
- Recent entries

### Permission Check
```
!dsd checkperms
```
Shows:
- Missing permissions
- Role hierarchy issues
- Channel access problems

## Recovery Steps

### Reset Configuration
```
!dsd config reset
```
Resets to default settings

### Reconnect Database
1. Stop bot
2. Verify database connection
3. Restart bot
4. Check logs

### Clear Cache
```
!dsd clearcache
```
Clears:
- Server configs
- Detection cache
- Command cooldowns

## Next Steps

After successful testing:
1. Document any issues found
2. Update configuration as needed
3. Monitor system for 24 hours
4. Collect user feedback

Remember to test in a controlled environment first before deploying changes to production servers.