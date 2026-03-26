# AI Therapist Backend

A Django REST Framework-based backend service that provides AI-powered emotional support and therapeutic responses. The system uses a GPT-Neo-125M language model to generate empathetic and supportive messages based on user mood inputs.

## Overview

This application allows users to express their feelings through emojis and thoughts, and receives AI-generated supportive responses. All interactions are stored in a database for tracking emotional well-being over time.

## Features

- **AI-Powered Support**: Uses EleutherAI's GPT-Neo-125M model for generating therapeutic responses
- **Mood Tracking**: Stores user mood entries with emojis, thoughts, and AI responses
- **RESTful API**: Built with Django REST Framework for easy integration
- **Lightweight & Fast**: Uses an efficient 125M parameter model optimized for quick responses
- **GPU Support**: Automatically utilizes CUDA if available for faster inference

## Technology Stack

- **Framework**: Django 6.0+ with Django REST Framework
- **AI Model**: EleutherAI GPT-Neo-125M (via HuggingFace Transformers)
- **Deep Learning**: PyTorch
- **Database**: SQLite (default, easily configurable for PostgreSQL/MySQL)
- **Deployment**: Gunicorn-ready with Procfile for easy deployment

## Installation

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

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

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (optional, for admin access)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**
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

#### 1. Get All Mood Entries
Retrieve all stored mood entries in reverse chronological order.

**Endpoint**: `GET /api/therapist/`

**Response**:
```json
[
  {
    "id": 1,
    "emoji": "😊",
    "thoughts": "Had a great day at work!",
    "ai_response": "That's wonderful to hear! It sounds like...",
    "created_at": "2026-03-26T10:30:00Z"
  }
]
```

#### 2. Create Mood Entry & Get AI Response
Submit a mood entry and receive an AI-generated supportive message.

**Endpoint**: `POST /api/therapist/`

**Request Body**:
```json
{
  "emoji": "😔",
  "thoughts": "Feeling overwhelmed with work deadlines"
}
```

**Response**:
```json
{
  "id": 2,
  "emoji": "😔",
  "thoughts": "Feeling overwhelmed with work deadlines",
  "ai_response": "I understand that work pressure can be challenging. It's important to...",
  "created_at": "2026-03-26T14:45:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Missing required fields (emoji or thoughts)
  ```json
  {
    "error": "emoji and thoughts are required"
  }
  ```

- `500 Internal Server Error`: Model generation failed
  ```json
  {
    "error": "model generation failed",
    "details": "Error message details"
  }
  ```

## Project Structure

```
ai_therapist_backend/
├── core/                   # Django project configuration
│   ├── settings.py         # Project settings
│   ├── urls.py            # Main URL routing
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration
├── therapist/             # Main application
│   ├── models.py          # MoodEntry database model
│   ├── views.py           # API view handlers
│   ├── serializers.py     # DRF serializers
│   ├── ai_model.py        # AI model initialization and inference
│   ├── urls.py            # App-specific routing
│   └── admin.py           # Django admin configuration
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── Procfile              # Deployment configuration (Gunicorn)
└── db.sqlite3            # SQLite database (created after migration)
```

## Model Details

### GPT-Neo-125M Configuration

The application uses EleutherAI's GPT-Neo-125M model with the following generation parameters:

- **max_new_tokens**: 120 (limits response length)
- **temperature**: 0.9 (controls randomness)
- **top_p**: 0.95 (nucleus sampling threshold)
- **do_sample**: True (enables sampling for varied responses)

The model is loaded once at startup and kept in memory for fast inference. It automatically uses GPU acceleration if CUDA is available.

## Development

### Running Tests
```bash
python manage.py test therapist
```

### Accessing Django Admin
1. Create a superuser (if not already done):
   ```bash
   python manage.py createsuperuser
   ```

2. Navigate to `http://127.0.0.1:8000/admin/`

3. Log in with your credentials to view and manage mood entries

### Making Migrations
After modifying models:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Deployment

The project includes a `Procfile` for deployment on platforms like Heroku, Railway, or Render.

### Heroku Deployment Example
```bash
heroku create your-app-name
git push heroku main
heroku run python manage.py migrate
```

### Production Considerations

1. **Update settings for production** in [core/settings.py](core/settings.py):
   - Set `DEBUG = False`
   - Configure `ALLOWED_HOSTS`
   - Use environment variables for `SECRET_KEY`
   - Configure a production database (PostgreSQL recommended)

2. **Add CORS headers** if needed for frontend integration:
   ```bash
   pip install django-cors-headers
   ```

3. **Set up static files**:
   ```bash
   python manage.py collectstatic
   ```

## Environment Variables (Recommended)

For production, consider using environment variables:

```python
# In settings.py
import os
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
```

## Performance Notes

- **First request**: May take 5-10 seconds as the model loads into memory
- **Subsequent requests**: 1-3 seconds per generation
- **GPU acceleration**: Significantly faster with CUDA-enabled GPU
- **Memory requirements**: ~500MB RAM for model loading

## Limitations

- The GPT-Neo-125M model is lightweight but may produce less coherent responses than larger models
- Responses are not clinically validated and should not replace professional therapy
- The model is pre-trained and not fine-tuned specifically for therapeutic conversations

## Future Enhancements

- User authentication and personalized tracking
- Fine-tuning the model on therapeutic conversation datasets
- Multi-language support
- Integration with larger models (GPT-Neo-2.7B, GPT-J-6B)
- Conversation history and context awareness
- Sentiment analysis and mood trend visualization

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is provided as-is for educational and personal use.

## Disclaimer

This application provides AI-generated supportive messages and is NOT a replacement for professional mental health services. If you're experiencing a mental health crisis, please contact a qualified mental health professional or emergency services.

## Support

For issues, questions, or contributions, please open an issue in the repository.

---

**Built with Django REST Framework and HuggingFace Transformers**
