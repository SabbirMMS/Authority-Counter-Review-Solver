from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

@dataclass( frozen = True )
class SignatureContext:
    name: str
    designation: str
    email: str
    phone: str

class SignatureTemplateService:
    def __init__( self, template_path: Path, context: SignatureContext ) -> None:
        self._template_path = template_path
        self._context = context

    def render( self ) -> str:
        if not self._template_path.exists():
            return ""

        template = self._template_path.read_text( encoding = "utf-8" )
        rendered = (
            template.replace( "{{SIGNATURE_NAME}}", escape( self._context.name, quote = True ) )
            .replace( "{{SIGNATURE_DESIGNATION}}", escape( self._context.designation, quote = True ) )
            .replace( "{{SIGNATURE_EMAIL}}", escape( self._context.email, quote = True ) )
            .replace( "{{SIGNATURE_PHONE}}", escape( self._context.phone, quote = True ) )
            .replace( "{{SIGNATURE_PHONE_TEL}}", escape( self._to_tel( self._context.phone ), quote = True ) )
        )
        return self._extract_body_content( rendered )

    @staticmethod
    def _extract_body_content( html: str ) -> str:
        match = re.search( r"<body[^>]*>(.*?)</body>", html, flags = re.IGNORECASE | re.DOTALL )
        if match:
            return match.group( 1 ).strip()
        return html.strip()

    @staticmethod
    def _to_tel( phone: str ) -> str:
        clean = re.sub( r"[^0-9+]","", phone )
        if clean.count( "+" ) > 1:
            clean = clean.replace( "+","" )
        if "+" in clean and not clean.startswith( "+" ):
            clean = clean.replace( "+","" )
        return clean