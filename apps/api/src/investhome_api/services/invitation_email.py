"""Invitation email copy. Does not log tokens or store credentials."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from urllib.parse import urljoin

INVITE_EMAIL_SUBJECT = "Investhome OS’e Davetlisiniz"
INVITE_LOGO_PATH = "/brand/logos/investhome-logo-white.png"
INVITE_HERO_PATH = "/brand/images/washington-dc-capitol-email.jpg"
CTA_LABEL = "Hesabımı Oluştur →"

_GOLD = "#C4A15A"
_BLACK = "#0B0B0B"
_TEXT = "#1A1A1A"
_MUTED = "#5C5C5C"
_PANEL = "#F6F6F6"
_WHITE = "#FFFFFF"
_FONT = "Arial, Helvetica, sans-serif"


@dataclass(frozen=True)
class InviteEmailContent:
    subject: str
    text_body: str
    html_body: str


def greeting_first_name(full_name: str) -> str:
    parts = [part for part in (full_name or "").strip().split() if part]
    return parts[0] if parts else ""


def format_invite_ttl_label(ttl_hours: int) -> str:
    hours = max(1, int(ttl_hours))
    if hours % 24 == 0:
        days = hours // 24
        return "1 gün" if days == 1 else f"{days} gün"
    return "1 saat" if hours == 1 else f"{hours} saat"


def invitation_asset_url(asset_base_url: str, path: str) -> str:
    base = (asset_base_url or "").strip().rstrip("/")
    relative = path if path.startswith("/") else f"/{path}"
    if not base:
        return relative
    return urljoin(f"{base}/", relative.lstrip("/"))


def build_invite_email(
    *,
    full_name: str,
    invite_url: str,
    ttl_hours: int,
    locale: str,
    from_name: str,
    invited_email: str = "",
    inviter_name: str = "",
    asset_base_url: str = "",
) -> InviteEmailContent:
    del locale  # Approved invitation is Turkish regardless of profile locale.
    del from_name
    first = greeting_first_name(full_name)
    hello = f"Merhaba {first}," if first else "Merhaba,"
    ttl_label = format_invite_ttl_label(ttl_hours)
    inviter = (inviter_name or "").strip() or "Investhome OS"
    email_addr = (invited_email or "").strip()
    logo_url = invitation_asset_url(asset_base_url, INVITE_LOGO_PATH)
    hero_url = invitation_asset_url(asset_base_url, INVITE_HERO_PATH)

    text_body = (
        "Investhome OS\n"
        "Amerika’da güven inşa ediyoruz.\n\n"
        "Investhome OS’e Hoş Geldiniz\n"
        "Projeler, yatırımlar, operasyon ve ekip tek platformda.\n\n"
        f"{hello}\n\n"
        "Sizi Investhome OS ekibine davet ediyoruz.\n\n"
        "Investhome OS; projelerimizi, yatırımlarımızı ve operasyonlarımızı "
        "daha hızlı, düzenli ve güvenli şekilde yönettiğimiz merkezi platformumuzdur.\n\n"
        "Kullanıcı hesabınızı oluşturmak için aşağıdaki bağlantıya tıklayın:\n\n"
        f"{invite_url}\n\n"
        f"Davet Eden: {inviter}\n"
        f"E-posta Adresiniz: {email_addr}\n"
        f"Bu davet bağlantısı {ttl_label} boyunca geçerlidir.\n\n"
        "Bu daveti beklemiyorsanız lütfen bu e-postayı dikkate almayın.\n"
        "Herhangi bir sorunuz olursa bizimle iletişime geçebilirsiniz.\n\n"
        "Investhome OS Ekibi\n"
    )
    html_body = _build_html(
        hello=hello,
        invite_url=invite_url,
        ttl_label=ttl_label,
        inviter=inviter,
        invited_email=email_addr,
        logo_url=logo_url,
        hero_url=hero_url,
    )
    return InviteEmailContent(
        subject=INVITE_EMAIL_SUBJECT,
        text_body=text_body,
        html_body=html_body,
    )


def _build_html(
    *,
    hello: str,
    invite_url: str,
    ttl_label: str,
    inviter: str,
    invited_email: str,
    logo_url: str,
    hero_url: str,
) -> str:
    href = escape(invite_url, quote=True)
    hello_h = escape(hello)
    inviter_h = escape(inviter)
    email_h = escape(invited_email)
    ttl_h = escape(ttl_label)
    logo_h = escape(logo_url, quote=True)
    hero_h = escape(hero_url, quote=True)
    cta = escape(CTA_LABEL)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(INVITE_EMAIL_SUBJECT)}</title>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<style type="text/css">
  @media only screen and (max-width: 620px) {{
    .ih-wrap {{ width: 100% !important; }}
    .ih-pad {{ padding-left: 18px !important; padding-right: 18px !important; }}
    .ih-hero-title {{ font-size: 22px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f3f3f3;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f3f3f3;">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" class="ih-wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:{_WHITE};border-collapse:collapse;">
        <tr>
          <td class="ih-pad" style="background-color:{_BLACK};padding:22px 28px 18px 28px;">
            <img src="{logo_h}" alt="Investhome" width="168" height="36" style="display:block;width:168px;height:auto;border:0;outline:none;text-decoration:none;">
            <p style="margin:12px 0 0 0;font-family:{_FONT};font-size:16px;line-height:1.3;color:{_WHITE};font-weight:bold;">Investhome OS</p>
            <p style="margin:4px 0 0 0;font-family:{_FONT};font-size:12px;line-height:1.4;color:{_GOLD};">Amerika’da güven inşa ediyoruz.</p>
          </td>
        </tr>
        <tr>
          <td background="{hero_h}" bgcolor="{_BLACK}" valign="bottom" width="600" height="280" style="background-color:{_BLACK};background-image:url('{hero_h}');background-size:cover;background-position:center;background-repeat:no-repeat;">
            <!--[if gte mso 9]>
            <v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" style="width:600px;height:280px;">
              <v:fill type="frame" src="{hero_h}" color="{_BLACK}" />
              <v:textbox inset="0,0,0,0">
            <![endif]-->
            <div>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td class="ih-pad" style="padding:72px 28px 28px 28px;">
                  <h1 class="ih-hero-title" style="margin:0;font-family:{_FONT};font-size:26px;line-height:1.25;color:{_WHITE};font-weight:bold;">Investhome OS’e Hoş Geldiniz</h1>
                  <p style="margin:10px 0 0 0;font-family:{_FONT};font-size:14px;line-height:1.45;color:{_WHITE};">Projeler, yatırımlar, operasyon ve ekip tek platformda.</p>
                </td>
              </tr>
            </table>
            </div>
            <!--[if gte mso 9]>
              </v:textbox>
            </v:rect>
            <![endif]-->
          </td>
        </tr>
        <tr>
          <td class="ih-pad" style="padding:32px 28px 8px 28px;font-family:{_FONT};font-size:15px;line-height:1.6;color:{_TEXT};">
            <p style="margin:0 0 16px 0;">{hello_h}</p>
            <p style="margin:0 0 16px 0;">Sizi Investhome OS ekibine davet ediyoruz.</p>
            <p style="margin:0 0 16px 0;">Investhome OS; projelerimizi, yatırımlarımızı ve operasyonlarımızı daha hızlı, düzenli ve güvenli şekilde yönettiğimiz merkezi platformumuzdur.</p>
            <p style="margin:0 0 24px 0;">Kullanıcı hesabınızı oluşturmak için aşağıdaki butona tıklayın.</p>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:0 28px 28px 28px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="center" bgcolor="{_GOLD}" style="background-color:{_GOLD};border-radius:6px;">
                  <a href="{href}" style="display:inline-block;padding:14px 32px;font-family:{_FONT};font-size:15px;font-weight:bold;color:{_WHITE};text-decoration:none;">{cta}</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td class="ih-pad" style="padding:0 28px 28px 28px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{_PANEL};border-radius:8px;">
              <tr>
                <td style="padding:18px 20px;font-family:{_FONT};font-size:13px;line-height:1.5;color:{_TEXT};">
                  <p style="margin:0 0 12px 0;"><strong>Davet Eden:</strong><br>{inviter_h}</p>
                  <p style="margin:0 0 12px 0;"><strong>E-posta Adresiniz:</strong><br>{email_h}</p>
                  <p style="margin:0;">Bu davet bağlantısı {ttl_h} boyunca geçerlidir.</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td class="ih-pad" style="padding:8px 28px 32px 28px;font-family:{_FONT};font-size:12px;line-height:1.6;color:{_MUTED};">
            <p style="margin:0 0 10px 0;">Bu daveti beklemiyorsanız lütfen bu e-postayı dikkate almayın.</p>
            <p style="margin:0 0 18px 0;">Herhangi bir sorunuz olursa bizimle iletişime geçebilirsiniz.</p>
            <p style="margin:0;color:{_TEXT};font-weight:bold;">Investhome OS Ekibi</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""
