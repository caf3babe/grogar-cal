# grogar-cal

**Gro**ß**r**ußbach **Gar**bage **Cal**endar: subscribable iCal feeds for the waste collection dates in Marktgemeinde Großrußbach.

## Feeds

The two zones differ only in the Altpapier dates:

| Feed | Zone |
| --- | --- |
| `grossrussbach-1.ics` | Großrußbach, Hipples, Weinsteig |
| `grossrussbach-2.ics` | Karnabrunn, Kleinebersdorf, Wetzleinsdorf |

Subscribe at `https://caf3babe.github.io/grogar-cal/grossrussbach-<zone>.ics`
(or with `webcal://` instead of `https://`).

## How it works

[GVU Korneuburg](https://korneuburg.umweltverbaende.at/fuer-die-bevoelkerung/abholtermine/) publishes official `.ics` files per zone, but at a URL that changes every year and in a format strict clients struggle with (Latin-1, vCal 1.0 params, 06:00 zero-length events).

`build.py` finds the current links on that page, re-parses the files and writes clean UTF-8 all-day calendars with stable UIDs. Each event carries two reminders: 19:00 the evening before and 06:15 on the day. Whether they fire depends on the client: Google Calendar ignores reminders in subscribed calendars, and Apple Calendar drops them by default. On the Mac, untick "Remove: Alerts" when subscribing; on iOS (iCloud subscription), turn off "Remove Alerts" via the ⓘ next to the calendar in the Calendar app, then remove and re-add the subscription so the reminders show up right away. A GitHub Actions workflow runs it monthly and on every push to `main`, then deploys the result to GitHub Pages. If the source page changes and the build fails, the previous calendars stay online and GitHub emails a failure notice.

```bash
python3 build.py public
```

## Setup

In the repo settings, set **Pages → Source** to **GitHub Actions**.
