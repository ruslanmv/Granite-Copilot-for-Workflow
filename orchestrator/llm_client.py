import os
from pathlib import Path
from dotenv import load_dotenv

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Retrieve required variables
api_key = os.getenv("WATSONX_APIKEY")
url = os.getenv("WATSONX_URL")
project_id = os.getenv("PROJECT_ID")

# Validate environment variables
if not api_key:
    raise ValueError("WATSONX_APIKEY is missing or empty.")
if not url:
    raise ValueError("WATSONX_URL is missing or empty.")
if not project_id:
    raise ValueError("PROJECT_ID is missing or empty.")

# Set up credentials and client
credentials = Credentials(url=url, api_key=api_key)
client = APIClient(credentials=credentials, project_id=project_id)

class LLMClient:
    """
    Wrapper around IBM watsonx.ai Granite foundation model inference.
    Provides text-generation, function-calling, and auto-fix capabilities.
    """

    def __init__(
        self,
        model_id: str = "ibm/granite-13b-instruct-v2",
        decoding_method: str = "greedy",
        max_new_tokens: int = 200,
    ):
        self.model_id = model_id
        self.client = client
        self.params = {
            GenParams.DECODING_METHOD: decoding_method,
            GenParams.MAX_NEW_TOKENS: max_new_tokens,
        }

    def generate_text(self, prompt: str, extra_params: dict = None) -> str:
        """
        Generate text from a prompt using the configured foundation model.
        """
        params = self.params.copy()
        if extra_params:
            params.update(extra_params)

        model = ModelInference(
            model_id=self.model_id,
            credentials=credentials,
            project_id=project_id,
        )
        response = model.generate_text(prompt=prompt, params=params)
        # response typically includes {"generated_text": "..."}
        return response.get("generated_text", str(response))

    def stream_text(self, prompt: str, extra_params: dict = None):
        """
        Stream text tokens from the model (if supported).
        Yields each chunk as it arrives.
        """
        params = self.params.copy()
        params[GenParams.STREAM] = True
        if extra_params:
            params.update(extra_params)

        model = ModelInference(
            model_id=self.model_id,
            credentials=credentials,
            project_id=project_id,
        )
        for chunk in model.generate_text(prompt=prompt, params=params):
            yield chunk

    def call_function(
        self, name: str, arguments: dict, prompt: str = ""
    ) -> dict:
        """
        Invoke a function-calling tool within the LLM via a structured prompt.
        Returns the function's JSON response.
        """
        func_payload = {
            "name": name,
            "arguments": arguments,
        }
        full_prompt = prompt or f"Call function `{name}` with arguments {arguments}."
        model = ModelInference(
            model_id=self.model_id,
            credentials=credentials,
            project_id=project_id,
        )
        response = model.generate_text(
            prompt=full_prompt,
            params={**self.params, GenParams.TOOL_FUNCTIONS: [func_payload]},
        )
        return response.get("function_response", {})

# Example usage (can be removed or moved to tests)
if __name__ == "__main__":
    client = LLMClient()
    sample_prompt = "Write a short story about a robot who wants to be a painter."
    result = client.generate_text(sample_prompt)
    print("Model response:", result)
