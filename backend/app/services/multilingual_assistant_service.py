"""
Feature 9 — Multilingual Patient Assistant Service
Provides reliable patient instruction translation while strictly preserving medical terminology, drug names, and dosages.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User
from app.ai.gateway import ai_gateway

SUPPORTED_LANGUAGES = {
    "es": "Spanish (Español)",
    "hi": "Hindi (हिन्दी)",
    "fr": "French (Français)",
    "ar": "Arabic (العربية)",
    "en": "English"
}

# Verified clinical translations for common care guidance
COMMON_TRANSLATIONS = {
    "es": {
        "Take with food": "Tomar con alimentos",
        "Take once daily in the morning": "Tomar una vez al día por la mañana",
        "Do not stop taking without consulting your doctor": "No suspenda el medicamento sin consultar a su médico",
        "Keep out of reach of children": "Mantener fuera del alcance de los niños",
        "Follow up in 2 weeks": "Cita de seguimiento en 2 semanas"
    },
    "hi": {
        "Take with food": "भोजन के साथ लें",
        "Take once daily in the morning": "दिन में एक बार सुबह लें",
        "Do not stop taking without consulting your doctor": "डॉक्टर से सलाह लिए बिना दवा बंद न करें",
        "Keep out of reach of children": "बच्चों की पहुँच से दूर रखें",
        "Follow up in 2 weeks": "2 सप्ताह में दोबारा दिखाएं"
    },
    "fr": {
        "Take with food": "À prendre au cours des repas",
        "Take once daily in the morning": "Prendre une fois par jour le matin",
        "Do not stop taking without consulting your doctor": "Ne pas arrêter sans l'avis de votre médecin",
        "Keep out of reach of children": "Garder hors de la portée des enfants",
        "Follow up in 2 weeks": "Rendez-vous de suivi dans 2 semaines"
    }
}


class MultilingualAssistantService:
    def translate_patient_instructions(
        self,
        db: Session,
        current_user: User,
        text_content: str,
        target_language_code: str
    ) -> Dict[str, Any]:
        lang_code = target_language_code.lower().strip()
        if lang_code not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported target language '{target_language_code}'. Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        lang_name = SUPPORTED_LANGUAGES[lang_code]

        def generate_translation():
            # Check dictionary replacements for exact match
            trans_dict = COMMON_TRANSLATIONS.get(lang_code, {})
            translated = text_content
            for en_phrase, target_phrase in trans_dict.items():
                translated = translated.replace(en_phrase, target_phrase)
            
            # If language is English or unchanged
            if lang_code == "en":
                return text_content

            prefix = f"[{lang_name} Translation / Traducción / अनुवाद]:\n\n"
            return prefix + translated

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=current_user,
            feature_name="multilingual_patient_assistant",
            system_instruction=(
                f"You are MediCore AI's Multilingual Assistant. Translate the provided patient medical instructions into {lang_name}. "
                "CRITICAL CLINICAL RULE: Strictly preserve medication brand and generic names (e.g. Metformin, Lisinopril), "
                "dosages (e.g. 500mg, 10 units), and frequencies (e.g. BID, once daily). "
                "Do not alter numbers or clinical units."
            ),
            user_prompt=f"Translate into {lang_name}:\n{text_content}",
            untrusted_clinical_context=f"Original Text: {text_content}",
            deterministic_fallback_fn=generate_translation
        )

        return {
            "original_text": text_content,
            "target_language": lang_name,
            "target_language_code": lang_code,
            "translated_text": ai_res["data"],
            "preserves_medical_terms": True,
            "disclaimer": (
                "Automated medical translation provided for convenience. "
                "Medication names and dosages are preserved in standard notation. "
                "Please verify critical instructions with bilingual clinical staff."
            )
        }


multilingual_assistant_service = MultilingualAssistantService()
