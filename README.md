# AI Therapist Backend

A Django REST Framework-based backend service that provides AI-powered emotional support and therapeutic responses. The system uses **Groq's Llama 3.1 8B Instant model** via cloud API to generate empathetic and supportive messages based on user mood inputs.

## Overview

This application allows users to express their feelings through emojis and thoughts, and receives AI-generated supportive responses. All interactions are stored in a database for tracking emotional well-being over time.

## Features

- **AI-Powered Support**: Uses Groq API with Llama 3.1 8B Instant model for generating therapeutic responses
- **Mood Tracking**: Stores user mood entries with emojis, thoughts, and AI responses
- **RESTful API**: Built with Django REST Framework for easy integration
- **Cloud-Based AI**: No local GPU/ML dependencies - uses Groq's fast cloud API
- **Production-Ready**: Railway/Heroku deployment with WhiteNoise for static files
- **Fast & Scalable**: Class-based views, efficient API calls, low memory footprint

## Technology Stack

- **Framework**: Django 5.1.4 with Django REST Framework 3.17.1
- **AI Model**: Groq API - Llama 3.1 8B Instant (cloud-based)
- **Database**: SQLite (default, easily configurable for PostgreSQL/MySQL)
- **HTTP Client**: Python `requests` library
- **Deployment**: Gunicorn + WhiteNoise for production
- **Platform**: Railway/Heroku ready with Procfile

## Installation

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)
- **Groq API Key** (get free key at [console.groq.com](https://console.groq.com))

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_therapist_backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export GROQ_API_KEY="your-groq-api-key-here"
   # Optional:
   export SECRET_KEY="your-secret-key"
   export DEBUG="True"  # Only for development
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (optional, for admin access)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

The server will start at `http://127.0.0.1:8000/`

## API Documentation

### Base URL
```
http://127.0.0.1:8000/api/therapist/
```

### Endpoints

#### 1. Get All Mood Entries (History)

Retrieve all stored mood entries in reverse chronological order (newest first).

**Endpoint**: `GET /api/therapist/history/`

**Response**:
```json
[
  {
    "id": 1,
    "emoji": "😊",
    "thoughts": "Had a great day at work!",
    "ai_response": "That's wonderful to hear! It sounds like things are going well...",
    "created_at": "2026-03-27T10:30:00Z"
  },
  {
    "id": 2,
    "emoji": "😔",
    "thoughts": "Feeling overwhelmed with deadlines",
    "ai_response": "I understand that work pressure can feel heavy. It's completely normal...",
    "created_at": "2026-03-26T14:45:00Z"
  }
]
```

#### 2. Create Mood Entry & Get AI Response

Submit a mood entry and receive an AI-generated supportive message.

**Endpoint**: `POST /api/therapist/generate/`

**Request Body**:
```json
{
  "emoji": "😔",
  "thoughts": "Feeling overwhelmed with work deadlines"
}
```

**Response** (200 OK):
```json
{
  "id": 3,
  "emoji": "😔",
  "thoughts": "Feeling overwhelmed with work deadlines",
  "ai_response": "I understand that work pressure can be challenging. Remember to take breaks and breathe. You're doing your best, and that's enough.",
  "created_at": "2026-03-27T14:45:00Z"
}
```

**Error Responses**:

- `400 Bad Request`: Missing required fields
  ```json
  {
    "error": "emoji and thoughts required"
  }
  ```

- `500 Internal Server Error`: API call failed (network error, invalid API key, etc.)

## Project Structure

```
ai_therapist_backend/
├── core/                   # Django project configuration
│   ├── settings.py         # Project settings (Railway-ready)
│   ├── urls.py            # Main URL routing
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration
├── therapist/             # Main application
│   ├── models.py          # MoodEntry database model
│   ├── views.py           # Class-based API views (APIView)
│   ├── serializers.py     # DRF serializers
│   ├── ai_model.py        # Groq API integration
│   ├── urls.py            # App-specific routing
│   └── admin.py           # Django admin configuration
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── Procfile              # Deployment configuration (Gunicorn)
└── db.sqlite3            # SQLite database (created after migration)
```

## Environment Variables

### Required

- **`GROQ_API_KEY`**: Your Groq API key (get from [console.groq.com](https://console.groq.com))
  ```bash
  export GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxx"
  ```

### Optional (Recommended for Production)

- **`SECRET_KEY`**: Django secret key (defaults to development key if not set)
- **`DEBUG`**: Set to `"True"` for development, `"False"` for production (default: False)

### Setting on Railway/Heroku

In your platform dashboard, add environment variables:
```
GROQ_API_KEY = gsk_xxxxxxxxxxxxxxxxxxxxx
SECRET_KEY = your-super-secret-random-key
DEBUG = False
```

## Model Details

### Groq API with Llama 3.1 8B Instant

The application uses Groq's cloud API with the following configuration:

- **Model**: `llama-3.1-8b-instant` (8 billion parameter Llama 3.1 model)
- **Provider**: Groq (cloud-based inference)
- **Speed**: ~1-2 seconds per response
- **System Prompt**: Configured for warm, supportive, empathetic responses
- **No Local Requirements**: No GPU, no ML libraries, minimal memory usage

**Benefits over local models**:
- ✅ No GPU/CUDA required
- ✅ Fast cold starts (no model loading)
- ✅ Better responses (8B model vs 125M)
- ✅ Low memory footprint (~100MB vs ~500MB)
- ✅ Easy deployment (no ML dependencies)

## Development

### Running Tests

```bash
python manage.py test therapist
```

**Note**: Mock the `generate_ai_response()` function in tests to avoid real API calls:

```python
from unittest.mock import patch

@patch('therapist.ai_model.generate_ai_response')
def test_create_mood_entry(self, mock_generate):
    mock_generate.return_value = "Mocked AI response"
    # ... your test code
```

### Accessing Django Admin

1. Create a superuser (if not already done):
   ```bash
   python manage.py createsuperuser
   ```

2. Navigate to `http://127.0.0.1:8000/admin/`

3. Log in with your credentials to view and manage mood entries

### Making Database Changes

After modifying models:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Deployment

The project is production-ready for Railway, Heroku, Render, or similar platforms.

### Railway Deployment

1. **Create a new project on Railway**

2. **Connect your GitHub repository**

3. **Add environment variables**:
   - `GROQ_API_KEY` = your Groq API key
   - `SECRET_KEY` = random secret key
   - `DEBUG` = False

4. **Deploy**: Railway auto-detects the Procfile and deploys

5. **Run migrations** (in Railway terminal):
   ```bash
   python manage.py migrate
   ```

### Heroku Deployment

```bash
heroku create your-app-name
heroku config:set GROQ_API_KEY="your-api-key"
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG="False"
git push heroku main
heroku run python manage.py migrate
```

### Production Checklist

Before deploying:

- [x] Static files configured (WhiteNoise ✓)
- [x] Environment variables for sensitive settings ✓
- [ ] **Set `GROQ_API_KEY`** (REQUIRED)
- [ ] Set strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Restrict `ALLOWED_HOSTS` to your domain
- [ ] Use PostgreSQL instead of SQLite
- [ ] Add CORS headers if frontend on different domain
- [ ] Set up error logging (Sentry, etc.)
- [ ] Configure rate limiting
- [ ] Set up monitoring and health checks

## Performance Notes

- **First request**: < 1 second (no model loading required)
- **Subsequent requests**: 1-2 seconds (API call time)
- **Memory usage**: ~50-100MB (no ML models in memory)
- **Scalability**: Limited by Groq API rate limits (very generous free tier)
- **No GPU needed**: All AI processing happens on Groq's servers

## API Usage & Costs

- Groq offers a **generous free tier** for development
- Production usage has very competitive pricing
- Each mood entry creation = 1 API call
- History retrieval = no API calls (database only)

**Recommendations**:
- Implement rate limiting to prevent abuse
- Monitor API usage via Groq dashboard
- Consider user quotas for high-scale deployments

## Limitations

- The AI provides supportive messages but is **NOT a replacement for professional therapy**
- Requires internet connection for AI responses
- Subject to Groq API rate limits and availability
- No user authentication (anyone can create/view entries)
- No data privacy controls (all entries visible to all users)
- No conversation history/context between entries

## Future Enhancements

- [ ] User authentication and personalized tracking
- [ ] User-specific mood history and analytics
- [ ] Multi-language support
- [ ] Conversation context (remember previous entries)
- [ ] Sentiment analysis and mood trend visualization
- [ ] Export mood journal as PDF/CSV
- [ ] Integration with other AI providers (OpenAI, Anthropic)
- [ ] Real-time streaming responses
- [ ] Mobile app integration
- [ ] Webhooks for mood alerts/reminders

## Integration Examples

### cURL

```bash
# Create mood entry
curl -X POST http://localhost:8000/api/therapist/generate/ \
  -H "Content-Type: application/json" \
  -d '{"emoji": "😊", "thoughts": "Had an amazing day!"}'

# Get history
curl http://localhost:8000/api/therapist/history/
```

### Python

```python
import requests

# Create mood entry
response = requests.post(
    'http://localhost:8000/api/therapist/generate/',
    json={'emoji': '😔', 'thoughts': 'Feeling stressed today'}
)
print(response.json())

# Get all entries
history = requests.get('http://localhost:8000/api/therapist/history/')
print(history.json())
```

### JavaScript

```javascript
// Create mood entry
fetch('http://localhost:8000/api/therapist/generate/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    emoji: '😊',
    thoughts: 'Feeling grateful today'
  })
})
.then(res => res.json())
.then(data => console.log(data));

// Get history
fetch('http://localhost:8000/api/therapist/history/')
.then(res => res.json())
.then(data => console.log(data));
```

## Troubleshooting

### Common Issues

1. **"emoji and thoughts required" error**
   - Ensure both `emoji` and `thoughts` fields are included in POST request

2. **500 Error on POST**
   - Check if `GROQ_API_KEY` environment variable is set
   - Verify API key is valid in Groq console
   - Check internet connection

3. **"GROQ_API_KEY" not found**
   ```bash
   export GROQ_API_KEY="your-api-key-here"
   ```

4. **Static files not loading in production**
   ```bash
   python manage.py collectstatic
   ```

5. **Database locked errors**
   - SQLite doesn't handle concurrent writes well
   - Use PostgreSQL for production

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is provided as-is for educational and personal use.

## Disclaimer

⚠️ **Important**: This application provides AI-generated supportive messages and is **NOT a replacement for professional mental health services**.

If you're experiencing a mental health crisis, please contact:
- **US**: National Suicide Prevention Lifeline: 988
- **UK**: Samaritans: 116 123
- **International**: [findahelpline.com](https://findahelpline.com)

## Support & Contact

- **Issues**: Open an issue in the GitHub repository
- **Questions**: Check existing issues or start a discussion
- **Groq API Docs**: [console.groq.com/docs](https://console.groq.com/docs)

---

**Built with Django REST Framework • Powered by Groq API (Llama 3.1 8B)**

**Last Updated**: March 27, 2026
