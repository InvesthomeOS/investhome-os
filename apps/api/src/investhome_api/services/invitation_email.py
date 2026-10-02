"""Invitation email copy. Does not log tokens or store credentials."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class InviteEmailContent:
    subject: str
    text_body: str
    html_body: str


def build_invite_email(
    *,
    full_name: str,
    invite_url: str,
    ttl_hours: int,
    locale: str,
    from_name: str,
) -> InviteEmailContent:
    name = (full_name or "").strip() or "there"
    hours = max(1, int(ttl_hours))
    brand = (from_name or "InvestHome OS").strip() or "InvestHome OS"
    turkish = (locale or "tr").lower().startswith("tr")
    if turkish:
        subject = f"{brand} daveti"
        text_body = (
            f"Merhaba {name},\n\n"
            f"{brand} platformuna davet edildiniz.\n"
            "Hesabınızı etkinleştirmek için aşağıdaki tek kullanımlık bağlantı ile şifrenizi oluşturun.\n\n"
            f"{invite_url}\n\n"
            f"Bu bağlantı {hours} saat geçerlidir ve yalnızca bir kez kullanılabilir.\n"
            "Bağlantıyı siz talep etmediyseniz bu e-postayı yok sayabilirsiniz.\n"
        )
        html_body = (
            "<!DOCTYPE html><html lang='tr'><body style='font-family:system-ui,sans-serif;line-height:1.5;color:#1a1a1a'>"
            f"<p>Merhaba {escape(name)},</p>"
            f"<p><strong>{escape(brand)}</strong> platformuna davet edildiniz.</p>"
            "<p>Hesabınızı etkinleştirmek için şifrenizi oluşturun. Bağlantı tek kullanımlıktır.</p>"
            f"<p><a href='{escape(invite_url, quote=True)}'>Daveti kabul et ve şifre oluştur</a></p>"
            f"<p>Geçerlilik süresi: {hours} saat. Bu bağlantı yalnızca bir kez kullanılabilir.</p>"
            "<p>Bu daveti beklemiyorsanız e-postayı yok sayabilirsiniz.</p>"
            "</body></html>"
        )
    else:
        subject = f"{brand} invitation"
        text_body = (
            f"Hello {name},\n\n"
            f"You have been invited to {brand}.\n"
            "Use the one-time link below to create your password and activate your account.\n\n"
            f"{invite_url}\n\n"
            f"This link expires in {hours} hours and can be used only once.\n"
            "If you did not expect this invitation, you can ignore this email.\n"
        )
        html_body = (
            "<!DOCTYPE html><html lang='en'><body style='font-family:system-ui,sans-serif;line-height:1.5;color:#1a1a1a'>"
            f"<p>Hello {escape(name)},</p>"
            f"<p>You have been invited to <strong>{escape(brand)}</strong>.</p>"
            "<p>Create your password to activate your account. This link is single-use.</p>"
            f"<p><a href='{escape(invite_url, quote=True)}'>Accept invitation and set password</a></p>"
            f"<p>Valid for {hours} hours. This link can be used only once.</p>"
            "<p>If you did not expect this invitation, you can ignore this email.</p>"
            "</body></html>"
        )
    return InviteEmailContent(subject=subject, text_body=text_body, html_body=html_body)
