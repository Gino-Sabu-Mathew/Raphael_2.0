# raphael_brain.py
# ==================================
from openai import OpenAI

# Initialize OpenAI client using your API key directly
client = OpenAI(api_key="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")

class RaphaelBrain:
    def __init__(self, model="gpt-4o-mini", system_prompt: str = None):
        self.model = model
        self.system_prompt = system_prompt or (
            "You are archangel Raphael's brain. Answer concisely and helpfully."
        )
        self.context = [{"role": "system", "content": self.system_prompt}]

    def ask(self, user_prompt: str, temperature: float = 0.3) -> str:
        self.context.append({"role": "user", "content": user_prompt})
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=self.context,
                temperature=temperature,
                max_tokens=512
            )
            answer = response.choices[0].message.content.strip()
            self.context.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            return f"[Brain Error: {str(e)}]"

# Quick test
if __name__ == "__main__":
    brain = RaphaelBrain()
    ans = brain.ask("Hello Raphael, how are you?")
    print("Raphael:", ans)