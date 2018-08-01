# Notepad

## A simple bot to safe some quick notes or reminders for you

- add `message`:                   Add `message` to your notepad
- rm  `idx`:                       Delete the message at `idx`
- rma:                             Clear your notepad
- show:                            Show your messages
- remindme `duration` [`message`]: Reminds you of this message for a `duration` (See formats below)
- snooze [`duration`]:             Reply to the reminder for this to snooze for a `duration` (Defaults to 5 minutes if not specifed)
- reboot notepad:                  Reboot this bot

### Valid formats for `duration`

You can provide duration in multiple formats. Duration currently allows you to pass weeks `w`, days `d`, hours `h`, and minutes `m`. They must be provided in order, but are all optional. See some examples below:

- 5w4d3h2m - 5 Weeks, 4 Days, 3 Hours, and 2 Minutes
- 4d2m     - 4 Days, 2 Minutes
- 2d       - 2 Days
- 30m      - 30 Minutes
- 30       - 30 Minutes (Backwards compatible. If no `m` is present, will default to minutes.)

Currently operates in the [SOBotics Room](https://chat.stackoverflow.com/rooms/111347/sobotics) on Stackoverflow. Please feel free to request additional functionality [here](https://github.com/SOBotics/notepad/issues) or in chat.
