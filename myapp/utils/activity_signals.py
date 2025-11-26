from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache

CACHE_KEY = 'site_recent_activity_events'
MAX_EVENTS = 200


def _push_event(event: dict):
    events = cache.get(CACHE_KEY, [])
    try:
        # Deduplicate recent identical events: if the newest event is the same
        # type/action/summary and occurred within 2 seconds, skip adding it.
        if events:
            first = events[0]
            t1 = first.get('type')
            a1 = first.get('action')
            s1 = first.get('summary')
            d1 = first.get('date')
            t2 = event.get('type')
            a2 = event.get('action')
            s2 = event.get('summary')
            d2 = event.get('date')
            if t1 == t2 and a1 == a2 and s1 == s2 and d1 and d2:
                try:
                    # total_seconds comparison; may raise if types unexpected
                    if abs((d1 - d2).total_seconds()) < 2:
                        return
                except Exception:
                    pass
    except Exception:
        # be defensive: if anything goes wrong with dedupe logic, continue
        pass

    events.insert(0, event)
    # trim
    if len(events) > MAX_EVENTS:
        events = events[:MAX_EVENTS]
    cache.set(CACHE_KEY, events, None)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    try:
        ev = {
            'type': 'Auth',
            'action': 'login',
            'summary': f"Login: {getattr(user, 'username', '')}",
            'detail': getattr(user, 'email', '') or getattr(user, 'username', ''),
            'link': 'mod_users',
            'date': timezone.now()
        }
        _push_event(ev)
    except Exception:
        # never raise from signal handlers
        pass


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    try:
        uname = getattr(user, 'username', None) if user else None
        ev = {
            'type': 'Auth',
            'action': 'logout',
            'summary': f"Logout: {uname if uname else 'Unknown'}",
            'detail': uname or '',
            'link': 'mod_users',
            'date': timezone.now()
        }
        _push_event(ev)
    except Exception:
        pass
