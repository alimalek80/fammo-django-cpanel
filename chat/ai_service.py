import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_SYSTEM_PROMPT = (
    "You are a helpful veterinary-style assistant that ONLY answers questions about PETS: dogs and cats.\n"
    "- If the user asks about anything unrelated to dogs/cats, respond briefly: "
    "'I only handle dog/cat topics. Please ask about dogs or cats.'\n"
    "- Support ANY language. Detect the user's language and reply in that language.\n"
    "- Keep tone friendly, concise, and practical. Don't give medical advice; suggest what needs to be done, "
    "  emphasize you are not a veterinarian, and recommend seeing a vet when needed.\n"
    "- IMPORTANT: Do NOT greet with 'Hi [name]' in every message. Only use casual greetings in the FIRST message. "
    "  In subsequent messages, address the user naturally by their first name when relevant (e.g., 'Great question, [name]!' "
    "  or '[name], based on your pet's profile...') without repeating 'Hi' each time.\n"
    "- If the user has NO name: address them as 'Dear user' and politely suggest: "
    "  'If you complete your profile, I can address you by your name!' Then answer their question.\n"
    "- When the user uploads an IMAGE:\n"
    "  • If it's a PET FOOD package/label: analyze the ingredients, nutritional information, and suitability for the user's pet. "
    "    Check against their pet's profile (breed, age, weight, allergies, health issues) and provide recommendations.\n"
    "  • If it's a PET PHOTO: help identify the breed, estimate age/size, note visible characteristics, and answer any questions about the pet.\n"
    "  • Be specific and helpful with image analysis, referencing details you can see in the image.\n"
)

def pet_answer(user_text: str, user_name: str | None = None, pet_profiles: str | None = None, is_first_message: bool = False, image_base64: str | None = None) -> str:
    """Answer a user question with optional personalization and image analysis.

    user_name: first name for friendly addressing (optional)
    pet_profiles: a plain-text summary of the user's pet(s). If multiple pets are present,
                  include all and specify their names. The assistant should use this data
                  when the question refers to "my pet" or a specific name. If ambiguous,
                  ask which pet the user means.
    is_first_message: True if this is the first message in the conversation (allows greeting)
    image_base64: base64-encoded image data (e.g., "image/jpeg;base64,/9j/4AAQ...") for vision analysis (optional)
    """
    system_parts = [BASE_SYSTEM_PROMPT]
    if user_name:
        greeting_note = " (This is the first message, so you may greet them with 'Hi [name]!')" if is_first_message else " (Use their name naturally in responses, not as a greeting)"
        system_parts.append(f"User first name: {user_name}{greeting_note}\n")
    else:
        system_parts.append("No user name available. Address as 'Dear user' and suggest profile completion.\n")
    
    if pet_profiles:
        system_parts.append(
            "Use the following pet profile data to tailor your answers. If information is missing, "
            "ask a brief clarifying question before giving detailed guidance.\n" + pet_profiles
        )

    system_prompt = "\n".join(system_parts)

    # Build user message content for Responses API
    user_content = []
    if user_text:
        user_content.append({"type": "input_text", "text": user_text})
    
    if image_base64:
        # OpenAI Responses API expects format: data:image/jpeg;base64,XXXX
        image_url = f"data:{image_base64}" if not image_base64.startswith("data:") else image_base64
        user_content.append({
            "type": "input_image",
            "image_url": image_url,
            "detail": "high"
        })

    # If no content at all, add placeholder
    if not user_content:
        user_content.append({"type": "input_text", "text": "Hello"})

    resp = client.responses.create(
        model="gpt-5",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )
    # Safe read
    return resp.output_text.strip() if getattr(resp, "output_text", None) else "Sorry, I couldn't generate a reply."
    system_parts = [BASE_SYSTEM_PROMPT]
    if user_name:
        greeting_note = " (This is the first message, so you may greet them with 'Hi [name]!')" if is_first_message else " (Use their name naturally in responses, not as a greeting)"
        system_parts.append(f"User first name: {user_name}{greeting_note}\n")
    else:
        system_parts.append("No user name available. Address as 'Dear user' and suggest profile completion.\n")
    
    if pet_profiles:
        system_parts.append(
            "Use the following pet profile data to tailor your answers. If information is missing, "
            "ask a brief clarifying question before giving detailed guidance.\n" + pet_profiles
        )

    system_prompt = "\n".join(system_parts)

    resp = client.responses.create(
        model="gpt-5",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
    )
    # Safe read
    return resp.output_text.strip() if getattr(resp, "output_text", None) else "Sorry, I couldn’t generate a reply."