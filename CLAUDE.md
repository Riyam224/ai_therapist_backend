# CLAUDE.md - AI Therapist Backend

Technical documentation for Claude Code to understand and work with this Django project.

## Project Overview

This is a Django REST Framework application that provides an AI-powered mental health support API. It uses the EleutherAI GPT-Neo-125M model to generate empathetic responses to user mood inputs.

## Architecture

### Application Structure

- **Django Project**: `core/` - Main project configuration
- **Django App**: `therapist/` - Main application handling mood entries and AI responses
- **Database**: SQLite (default), easily swappable for PostgreSQL/MySQL
- **AI Model**: Loaded once at startup in [therapist/ai_model.py](therapist/ai_model.py)

### Key Components

1. **Model Layer** ([therapist/models.py](therapist/models.py))
   - `MoodEntry`: Stores user mood data
     - Fields: `emoji`, `thoughts`, `ai_response`, `created_at`
     - Uses auto-generated timestamps
     - String representation shows emoji and truncated thoughts

2. **View Layer** ([therapist/views.py](therapist/views.py))
   - `ai_therapist`: Combined GET/POST view
     - GET: Returns all mood entries ordered by `created_at` DESC
     - POST: Creates new mood entry with AI-generated response
     - Validates required fields: `emoji` and `thoughts`
     - Error handling for model generation failures

3. **AI Model** ([therapist/ai_model.py](therapist/ai_model.py))
   - Uses `EleutherAI/gpt-neo-125M` from HuggingFace
   - Model loaded at module import (singleton pattern)
   - GPU-aware: Uses CUDA if available, falls back to CPU
   - Generation parameters:
     - `max_new_tokens=120`
     - `temperature=0.9`
     - `top_p=0.95`
     - `do_sample=True`

4. **Serializer** ([therapist/serializers.py](therapist/serializers.py))
   - `MoodEntrySerializer`: Standard DRF ModelSerializer
   - Exposes all fields: `id`, `emoji`, `thoughts`, `ai_response`, `created_at`

### URL Routing

- **Main URLs** ([core/urls.py](core/urls.py)):
  - `/admin/` → Django admin interface
  - `/api/therapist/` → Includes therapist app URLs

- **Therapist URLs** ([therapist/urls.py](therapist/urls.py)):
  - `` (empty path) → `ai_therapist` view (GET/POST)
  - `generate/` → Same `ai_therapist` view (alternate endpoint)

## Development Conventions

### Code Style

- Arabic comments present in codebase - maintain when editing existing comments
- PEP 8 compliant
- Django naming conventions followed
- DRF best practices applied

### Database

- SQLite for development (file: `db.sqlite3`)
- Migrations managed in standard Django way
- Model uses auto-timestamps (`auto_now_add=True`)

### Dependencies

**Core** ([requirements.txt](requirements.txt)):
- `Django>=4.0` - Web framework
- `djangorestframework` - REST API
- `transformers` - HuggingFace model loading
- `torch` - PyTorch for model inference
- `gunicorn` - Production WSGI server

### Testing

- Test file exists: [therapist/tests.py](therapist/tests.py)
- Currently minimal - good opportunity for expansion
- Run with: `python manage.py test therapist`

## Common Tasks

### Adding New Features

When adding features, follow this structure:

1. **Database Changes**:
   - Modify [therapist/models.py](therapist/models.py)
   - Run: `python manage.py makemigrations && python manage.py migrate`

2. **API Changes**:
   - Update [therapist/serializers.py](therapist/serializers.py) if needed
   - Modify [therapist/views.py](therapist/views.py)
   - Add routes in [therapist/urls.py](therapist/urls.py)

3. **AI Model Changes**:
   - Modify [therapist/ai_model.py](therapist/ai_model.py)
   - Be aware: model loads at startup (module import)
   - First request after startup may be slow

### Working with the AI Model

**Important Notes**:
- Model is loaded once at module import in [therapist/ai_model.py](therapist/ai_model.py)
- Changing `MODEL_NAME` requires server restart
- Model stays in memory (~500MB)
- Generation is synchronous - blocks request until complete
- Consider async or Celery for production with larger models

**Generation Function**:
```python
generate_support_message(emoji: str, thoughts: str) -> str
```
- Constructs prompt from emoji and thoughts
- Returns cleaned response text (prompt removed)
- May raise exceptions - caller should handle

### Security Considerations

**Current Issues** ([core/settings.py](core/settings.py)):
- `DEBUG = True` - Must set to False in production
- `SECRET_KEY` is hardcoded - Use environment variable
- `ALLOWED_HOSTS = []` - Configure for production
- No CORS headers - Add `django-cors-headers` if frontend needed
- CSRF enabled - Keep enabled unless token-based auth added

**Before Production**:
1. Set environment variables for sensitive settings
2. Configure proper database (PostgreSQL recommended)
3. Add authentication if needed
4. Set up HTTPS/SSL
5. Configure CORS if frontend on different domain

### Running Commands

**Development**:
```bash
python manage.py runserver  # Start dev server
python manage.py migrate    # Apply migrations
python manage.py makemigrations  # Create migrations
python manage.py createsuperuser  # Create admin user
python manage.py shell      # Django shell
```

**Production** (uses Gunicorn per [Procfile](Procfile)):
```bash
gunicorn core.wsgi --log-file -
```

## API Behavior

### POST Request Flow

1. Request received at `POST /api/therapist/`
2. View validates `emoji` and `thoughts` presence
3. `generate_support_message()` called with inputs
4. Model generates response (1-3 seconds typically)
5. `MoodEntry` created with all data
6. Serialized response returned

### Error Handling

- **400**: Missing required fields → `{"error": "emoji and thoughts are required"}`
- **500**: Model generation fails → `{"error": "model generation failed", "details": "..."}`
- No rate limiting currently implemented
- No input sanitization beyond Django's default

## File Organization

```
ai_therapist_backend/
├── core/                  # Django project config
│   ├── __init__.py
│   ├── asgi.py           # ASGI entry point
│   ├── wsgi.py           # WSGI entry point (used by Gunicorn)
│   ├── settings.py       # All Django settings
│   └── urls.py           # Root URL configuration
├── therapist/            # Main app
│   ├── __init__.py
│   ├── admin.py          # Admin site config
│   ├── apps.py           # App configuration
│   ├── models.py         # MoodEntry model
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   ├── ai_model.py       # AI model singleton
│   ├── urls.py           # App URL patterns
│   ├── tests.py          # Test cases
│   └── migrations/       # Database migrations
├── .venv/                # Virtual environment
├── manage.py             # Django CLI
├── requirements.txt      # Python dependencies
├── Procfile             # Gunicorn config for deployment
├── db.sqlite3           # SQLite database
└── .gitignore           # Git ignore rules
```

## Performance Characteristics

- **Cold Start**: 5-10 seconds (model loading)
- **Warm Request**: 1-3 seconds (generation time)
- **Memory**: ~500MB for model
- **CPU vs GPU**:
  - CPU: 2-5 seconds per generation
  - GPU: 0.5-1 second per generation

## Extension Points

### Easy Additions

1. **User Authentication**: Add Django auth or JWT tokens
2. **User-Specific Entries**: Add ForeignKey to User model
3. **Filtering**: Add query parameters for date ranges, emoji filters
4. **Pagination**: Add DRF pagination classes
5. **Rate Limiting**: Add throttling to prevent abuse

### Model Improvements

1. **Larger Models**: Upgrade to GPT-Neo-2.7B or GPT-J-6B for better responses
2. **Fine-tuning**: Fine-tune on therapeutic conversation datasets
3. **Context**: Add conversation history for context-aware responses
4. **Async**: Use Celery or Django Channels for non-blocking generation

### Data Features

1. **Analytics**: Aggregate mood trends over time
2. **Sentiment Analysis**: Add sentiment scoring
3. **Export**: Allow users to export their mood journal
4. **Insights**: Generate weekly/monthly summaries

## Testing Strategy

When writing tests, focus on:

1. **View Tests**: Test GET/POST endpoints, validation, error cases
2. **Model Tests**: Test MoodEntry creation, string representation
3. **AI Model Tests**: Mock the model for fast tests, separate integration tests
4. **Serializer Tests**: Test field inclusion, validation

Example test structure:
```python
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

class TherapistAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('therapist.ai_model.generate_support_message')
    def test_create_mood_entry(self, mock_generate):
        mock_generate.return_value = "Mocked response"
        # ... test code
```

## Known Limitations

1. **No Authentication**: Anyone can create/read entries
2. **No Data Privacy**: All entries visible to all users
3. **Synchronous AI**: Blocks request during generation
4. **Small Model**: GPT-Neo-125M may produce less coherent responses
5. **No Rate Limiting**: Vulnerable to spam/abuse
6. **No Input Validation**: Only checks for field presence
7. **Hardcoded Settings**: Many production settings need environment variables

## Deployment Checklist

Before deploying:

- [ ] Set `DEBUG = False` in [core/settings.py](core/settings.py)
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use environment variables for `SECRET_KEY`
- [ ] Set up production database (PostgreSQL)
- [ ] Configure static files (`STATIC_ROOT`, `collectstatic`)
- [ ] Add error logging (Sentry, CloudWatch, etc.)
- [ ] Set up HTTPS/SSL
- [ ] Add CORS headers if needed
- [ ] Configure rate limiting
- [ ] Set up monitoring (health checks, performance)
- [ ] Add authentication if needed
- [ ] Review database indexes for performance
- [ ] Set up automated backups

## Environment Variables (Recommended)

```bash
# Production settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:pass@host:5432/dbname

# Optional
CUDA_VISIBLE_DEVICES=0  # GPU selection
MODEL_NAME=EleutherAI/gpt-neo-125M  # Model override
```

## Debugging Tips

1. **Model Not Loading**: Check memory, try CPU-only mode
2. **Slow Responses**: First request is slow (model loading), subsequent faster
3. **CUDA Errors**: Set `device = torch.device("cpu")` in [therapist/ai_model.py](therapist/ai_model.py)
4. **Database Locked**: SQLite doesn't handle concurrent writes well - use PostgreSQL
5. **Import Errors**: Activate virtual environment first

## Integration Examples

### cURL
```bash
# Create mood entry
curl -X POST http://localhost:8000/api/therapist/ \
  -H "Content-Type: application/json" \
  -d '{"emoji": "😊", "thoughts": "Great day!"}'

# Get all entries
curl http://localhost:8000/api/therapist/
```

### Python Requests
```python
import requests

response = requests.post(
    'http://localhost:8000/api/therapist/',
    json={'emoji': '😊', 'thoughts': 'Great day!'}
)
print(response.json())
```

### JavaScript Fetch
```javascript
fetch('http://localhost:8000/api/therapist/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({emoji: '😊', thoughts: 'Great day!'})
})
.then(res => res.json())
.then(data => console.log(data));
```

---

**Last Updated**: 2026-03-26
**Django Version**: 6.0.3
**Python Version**: 3.13
