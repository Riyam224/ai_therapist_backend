# CLAUDE.md - AI Therapist Backend

Technical documentation for Claude Code to understand and work with this Django project.

## Project Overview

This is a Django REST Framework application that provides an AI-powered mental health support API. It uses the **Groq API with Llama 3.1 8B Instant model** to generate empathetic responses to user mood inputs.

## Architecture

### Application Structure

- **Django Project**: `core/` - Main project configuration
- **Django App**: `therapist/` - Main application handling mood entries and AI responses
- **Database**: SQLite (default), easily swappable for PostgreSQL/MySQL
- **AI Service**: Groq API (external REST API) accessed via [therapist/ai_model.py](therapist/ai_model.py)
- **Deployment**: Railway-ready with WhiteNoise for static files

### Key Components

1. **Model Layer** ([therapist/models.py](therapist/models.py))
   - `MoodEntry`: Stores user mood data
     - Fields: `emoji`, `thoughts`, `ai_response`, `created_at`
     - Uses auto-generated timestamps (`auto_now_add=True`)
     - String representation shows emoji and truncated thoughts (first 20 chars)
     - Meta: `verbose_name` and `verbose_name_plural` configured

2. **View Layer** ([therapist/views.py](therapist/views.py))
   - Uses **class-based APIView** (DRF)
   - `GenerateResponseAPIView`: POST-only endpoint
     - Validates required fields: `emoji` and `thoughts`
     - Calls `generate_ai_response()` from ai_model
     - Creates `MoodEntry` and returns serialized data
     - Returns 400 if fields missing, 200 on success
   - `AllHistoryAPIView`: GET-only endpoint
     - Returns all mood entries ordered by `created_at` DESC
     - Returns serialized list of all entries

3. **AI Service** ([therapist/ai_model.py](therapist/ai_model.py))
   - Uses **Groq API** (external cloud service)
   - Model: `llama-3.1-8b-instant`
   - Requires `GROQ_API_KEY` environment variable
   - Makes REST API call to `https://api.groq.com/openai/v1/chat/completions`
   - System prompt: Warm, supportive AI therapist with empathetic responses
   - **No local model loading** - stateless API calls

4. **Serializer** ([therapist/serializers.py](therapist/serializers.py))
   - `MoodEntrySerializer`: Standard DRF ModelSerializer
   - Uses `fields = "__all__"` to expose all model fields
   - Automatically handles: `id`, `emoji`, `thoughts`, `ai_response`, `created_at`

### URL Routing

- **Main URLs** ([core/urls.py](core/urls.py)):
  - `/admin/` → Django admin interface
  - `/api/therapist/` → Includes therapist app URLs

- **Therapist URLs** ([therapist/urls.py](therapist/urls.py)):
  - `generate/` → `GenerateResponseAPIView` (POST only)
  - `history/` → `AllHistoryAPIView` (GET only)

### Full API Endpoints

- `POST /api/therapist/generate/` - Create mood entry with AI response
- `GET /api/therapist/history/` - Retrieve all mood entries

## Development Conventions

### Code Style

- Arabic comments present in codebase - maintain when editing existing comments
- PEP 8 compliant
- Django naming conventions followed
- DRF best practices applied (class-based views, serializers)

### Database

- SQLite for development (file: `db.sqlite3`)
- Migrations managed in standard Django way
- Model uses auto-timestamps (`auto_now_add=True`)

### Dependencies

**Core** ([requirements.txt](requirements.txt)):
- `Django==5.1.4` - Web framework
- `djangorestframework==3.17.1` - REST API
- `requests==2.33.0` - HTTP client for Groq API calls
- `gunicorn==25.3.0` - Production WSGI server
- `whitenoise==6.5.0` - Static file serving for production
- `certifi==2026.2.25` - SSL certificate bundle

**Note**: No `torch` or `transformers` - uses external API instead of local model.

### Testing

- Test file exists: [therapist/tests.py](therapist/tests.py)
- Currently minimal - good opportunity for expansion
- Run with: `python manage.py test therapist`
- When testing, mock the `generate_ai_response()` function to avoid real API calls

## Common Tasks

### Adding New Features

When adding features, follow this structure:

1. **Database Changes**:
   - Modify [therapist/models.py](therapist/models.py)
   - Run: `python manage.py makemigrations && python manage.py migrate`

2. **API Changes**:
   - Update [therapist/serializers.py](therapist/serializers.py) if needed
   - Modify or add views in [therapist/views.py](therapist/views.py)
   - Add routes in [therapist/urls.py](therapist/urls.py)

3. **AI Service Changes**:
   - Modify [therapist/ai_model.py](therapist/ai_model.py)
   - No server restart needed (stateless API calls)
   - Can change model, system prompt, or API parameters

### Working with the AI Service

**Important Notes**:
- Uses **Groq API** - requires `GROQ_API_KEY` environment variable
- No local model loading - each request makes an API call
- API calls are synchronous - blocks request until complete
- Typical response time: 1-2 seconds (network + API processing)
- Requires internet connection

**Generation Function**:
```python
generate_ai_response(emoji: str, thoughts: str) -> str
```
- Makes POST request to Groq API
- Uses `llama-3.1-8b-instant` model
- Constructs chat messages with system prompt and user input
- Returns AI-generated response text
- May raise exceptions (network errors, API errors) - caller should handle

**API Configuration**:
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`
- Model: `llama-3.1-8b-instant` (8B parameter Llama 3.1)
- System prompt emphasizes empathy, warmth, short responses

### Security Considerations

**Current State** ([core/settings.py](core/settings.py)):
- ✅ `SECRET_KEY` uses environment variable with fallback
- ✅ `DEBUG` uses environment variable (defaults to False)
- ✅ `ALLOWED_HOSTS` configured for Railway deployment (`["*", ".railway.app"]`)
- ✅ WhiteNoise configured for secure static file serving
- ⚠️ `ALLOWED_HOSTS = ["*"]` allows all hosts - restrict in production
- ⚠️ No CORS headers - Add `django-cors-headers` if frontend needed
- ⚠️ CSRF enabled - Keep enabled unless token-based auth added

**Environment Variables Required**:
- `GROQ_API_KEY` - **Required** for AI functionality
- `SECRET_KEY` - Optional (has fallback for dev)
- `DEBUG` - Optional (defaults to False)

**Before Production**:
1. ✅ Set `GROQ_API_KEY` environment variable
2. ✅ Set `SECRET_KEY` environment variable to strong random value
3. ⚠️ Restrict `ALLOWED_HOSTS` to specific domains
4. ⚠️ Add authentication if needed
5. ⚠️ Set up HTTPS/SSL (Railway provides this)
6. ⚠️ Configure CORS if frontend on different domain
7. ⚠️ Consider rate limiting to prevent API cost abuse

### Running Commands

**Development**:
```bash
# Set API key
export GROQ_API_KEY="your-api-key-here"

# Standard Django commands
python manage.py runserver  # Start dev server
python manage.py migrate    # Apply migrations
python manage.py makemigrations  # Create migrations
python manage.py createsuperuser  # Create admin user
python manage.py shell      # Django shell
python manage.py collectstatic  # Collect static files
```

**Production** (uses Gunicorn per [Procfile](Procfile)):
```bash
gunicorn core.wsgi --log-file -
```

## API Behavior

### POST Request Flow (Generate Endpoint)

1. Request received at `POST /api/therapist/generate/`
2. `GenerateResponseAPIView.post()` validates `emoji` and `thoughts` presence
3. `generate_ai_response()` called with inputs
4. Groq API request made (1-2 seconds typically)
5. `MoodEntry` created with emoji, thoughts, and AI response
6. Serialized response returned with 200 status

### GET Request Flow (History Endpoint)

1. Request received at `GET /api/therapist/history/`
2. `AllHistoryAPIView.get()` queries all MoodEntry objects
3. Entries ordered by `created_at` descending (newest first)
4. All entries serialized and returned as JSON array

### Error Handling

- **400**: Missing required fields → `{"error": "emoji and thoughts required"}`
- **500**: API call fails → Exception raised (network error, API error, etc.)
- No rate limiting currently implemented
- No input sanitization beyond Django's default
- API errors not caught - will return 500

## File Organization

```
ai_therapist_backend/
├── core/                  # Django project config
│   ├── __init__.py
│   ├── asgi.py           # ASGI entry point
│   ├── wsgi.py           # WSGI entry point (used by Gunicorn)
│   ├── settings.py       # All Django settings (Railway-ready)
│   └── urls.py           # Root URL configuration
├── therapist/            # Main app
│   ├── __init__.py
│   ├── admin.py          # Admin site config
│   ├── apps.py           # App configuration
│   ├── models.py         # MoodEntry model
│   ├── views.py          # Class-based APIViews
│   ├── serializers.py    # DRF serializers
│   ├── ai_model.py       # Groq API integration
│   ├── urls.py           # App URL patterns
│   ├── tests.py          # Test cases
│   └── migrations/       # Database migrations
├── staticfiles/          # Collected static files (generated)
├── .venv/                # Virtual environment
├── manage.py             # Django CLI
├── requirements.txt      # Python dependencies
├── Procfile             # Gunicorn config for Railway/Heroku
├── db.sqlite3           # SQLite database
└── .gitignore           # Git ignore rules
```

## Performance Characteristics

- **Cold Start**: < 1 second (no model loading)
- **API Request**: 1-2 seconds (network + Groq API processing)
- **Memory**: Minimal (~50-100MB, no ML models in memory)
- **Scalability**: Limited by Groq API rate limits and costs
- **No GPU Required**: All processing happens on Groq's servers

## Extension Points

### Easy Additions

1. **User Authentication**: Add Django auth or JWT tokens
2. **User-Specific Entries**: Add ForeignKey to User model
3. **Filtering**: Add query parameters for date ranges, emoji filters
4. **Pagination**: Add DRF pagination classes to history endpoint
5. **Rate Limiting**: Add DRF throttling to prevent API abuse
6. **Error Handling**: Wrap Groq API calls in try/except with proper error responses

### API Service Improvements

1. **Async Calls**: Use async/await for non-blocking API requests
2. **Caching**: Cache common responses to reduce API costs
3. **Retry Logic**: Add retries with exponential backoff for failed API calls
4. **Streaming**: Use streaming responses for real-time AI generation
5. **Model Selection**: Allow users to choose different Groq models
6. **Context**: Add conversation history to API calls for context-aware responses

### Data Features

1. **Analytics**: Aggregate mood trends over time
2. **Sentiment Analysis**: Add sentiment scoring
3. **Export**: Allow users to export their mood journal
4. **Insights**: Generate weekly/monthly summaries using AI

## Testing Strategy

When writing tests, focus on:

1. **View Tests**: Test POST/GET endpoints, validation, error cases
2. **Model Tests**: Test MoodEntry creation, string representation
3. **AI Service Tests**: **Mock the API calls** for fast tests, separate integration tests
4. **Serializer Tests**: Test field inclusion, validation

Example test structure:
```python
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

class TherapistAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('therapist.ai_model.generate_ai_response')
    def test_create_mood_entry(self, mock_generate):
        mock_generate.return_value = "Mocked AI response"
        response = self.client.post(
            '/api/therapist/generate/',
            {'emoji': '😊', 'thoughts': 'Great day!'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('ai_response', response.data)
```

## Known Limitations

1. **No Authentication**: Anyone can create/read entries
2. **No Data Privacy**: All entries visible to all users
3. **Synchronous API Calls**: Blocks request during generation
4. **No Error Handling**: API failures cause 500 errors
5. **No Rate Limiting**: Vulnerable to spam/abuse (costs money)
6. **API Dependency**: Requires internet and Groq API availability
7. **No Input Validation**: Only checks for field presence
8. **API Costs**: Each request costs money (Groq pricing)

## Deployment Checklist

Before deploying to Railway/Heroku/etc:

- [x] Set `DEBUG = False` in production (via environment variable)
- [x] Configure `ALLOWED_HOSTS` (partially done - refine for production)
- [x] Use environment variables for `SECRET_KEY`
- [x] Static files configured with WhiteNoise
- [ ] **Set `GROQ_API_KEY` environment variable** (CRITICAL)
- [ ] Restrict `ALLOWED_HOSTS` to specific domain
- [ ] Set up production database (PostgreSQL recommended)
- [ ] Add error logging (Sentry, CloudWatch, etc.)
- [ ] Add CORS headers if needed
- [ ] Configure rate limiting (DRF throttling)
- [ ] Set up monitoring (health checks, API cost tracking)
- [ ] Add authentication if needed
- [ ] Review database indexes for performance
- [ ] Set up automated backups

## Environment Variables

**Required**:
```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx  # From Groq Console
```

**Recommended**:
```bash
SECRET_KEY=your-super-secret-random-key-here
DEBUG=False
```

**Railway/Heroku**: Set these in the platform dashboard under Environment Variables.

## Debugging Tips

1. **API Not Working**: Check `GROQ_API_KEY` is set correctly
2. **Slow Responses**: Normal - API calls take 1-2 seconds
3. **401 Unauthorized**: Invalid or missing `GROQ_API_KEY`
4. **500 Errors**: Check logs for API error details (rate limits, network issues)
5. **Database Locked**: SQLite doesn't handle concurrent writes well - use PostgreSQL
6. **Import Errors**: Activate virtual environment first
7. **Static Files 404**: Run `python manage.py collectstatic`

## Integration Examples

### cURL
```bash
# Create mood entry with AI response
curl -X POST http://localhost:8000/api/therapist/generate/ \
  -H "Content-Type: application/json" \
  -d '{"emoji": "😊", "thoughts": "Had a great day at work!"}'

# Get all mood entries
curl http://localhost:8000/api/therapist/history/
```

### Python Requests
```python
import requests

# Generate AI response
response = requests.post(
    'http://localhost:8000/api/therapist/generate/',
    json={'emoji': '😔', 'thoughts': 'Feeling overwhelmed today'}
)
print(response.json())

# Get history
history = requests.get('http://localhost:8000/api/therapist/history/')
print(history.json())
```

### JavaScript Fetch
```javascript
// Create mood entry
fetch('http://localhost:8000/api/therapist/generate/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({emoji: '😊', thoughts: 'Great day!'})
})
.then(res => res.json())
.then(data => console.log(data));

// Get history
fetch('http://localhost:8000/api/therapist/history/')
.then(res => res.json())
.then(data => console.log(data));
```

## API Cost Considerations

- Groq API is **paid service** (though very affordable)
- Each mood entry creation = 1 API call
- No cost for history retrieval (database only)
- Consider implementing:
  - Rate limiting to prevent abuse
  - User quotas for API usage
  - Caching for repeated queries
  - Usage analytics and cost monitoring

## Migration from Old Architecture

This project previously used:
- Local HuggingFace GPT-Neo-125M model
- `transformers` and `torch` dependencies
- Function-based views
- Combined GET/POST endpoint

Now uses:
- ✅ Groq Cloud API (Llama 3.1 8B)
- ✅ `requests` library only (no ML dependencies)
- ✅ Class-based APIViews (DRF best practice)
- ✅ Separate generate/history endpoints

**Benefits**:
- No GPU/CPU requirements
- Faster cold starts (no model loading)
- Better AI responses (larger 8B model)
- Lower memory usage (~500MB → ~100MB)
- Easier deployment (no ML dependencies)

---

**Last Updated**: 2026-03-27
**Django Version**: 5.1.4
**Python Version**: 3.13
**AI Provider**: Groq API (Llama 3.1 8B Instant)
