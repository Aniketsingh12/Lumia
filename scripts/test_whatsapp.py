"""Test WhatsApp webhook locally using a simulated payload."""
import httpx
import json

WEBHOOK_URL = "http://localhost:8000/api/channels/whatsapp/webhook"

test_payload = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "919876543210",
                                "type": "text",
                                "text": {"body": "Do you ship to Mumbai?"},
                            }
                        ],
                        "contacts": [
                            {"profile": {"name": "Test User"}}
                        ],
                    }
                }
            ]
        }
    ]
}


def test():
    print("Sending test WhatsApp webhook payload...")
    print(f"URL: {WEBHOOK_URL}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print()

    response = httpx.post(WEBHOOK_URL, json=test_payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


if __name__ == "__main__":
    test()
