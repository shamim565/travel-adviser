# Travel Adviser

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.13 or higher is installed. [Download Python](https://www.python.org/downloads/)
- `pip` (Python package manager) is installed.
- A virtual environment tool such as `pipenv` is available.
- Git is installed. [Download Git](https://git-scm.com/)
- Redis is installed and running. [Download Redis](https://redis.io/download)

## Installation

Please Follow these steps to set up the project:

1. **Clone the Repository**

   ```bash
   git clone git@github.com:shamim565/travel-adviser.git
   cd travel_adviser
   ```

2. **Set Up a Virtual Environment**

   ```bash
   pip install pipenv
   pipenv shell
   ```

3. **Install Dependencies**

   ```bash
   pipenv install
   ```

4. **Set Up Environment Variables**  
   Create a `.env` file in the project root and add the necessary environment variables from `env.example`.

5. **Apply Migrations**

   ```bash
   python manage.py migrate
   ```

6. **Run Redis**

   Start Redis in a separate terminal:

   ```bash
   redis-server
   ```

7. **Start Celery Worker**

   For **Linux** and **Mac**:

   ```bash
   celery -A config worker --loglevel=info
   ```

   For **Windows**:

   ```bash
   celery -A config worker -l info -P solo
   ```

8. **Start Celery Beat**

   For **Linux** and **Mac**:

   ```bash
   celery -A config beat --loglevel=info
   ```

   For **Windows**:

   ```bash
   celery -A config beat -l info
   ```

9. **Initiate a Task (First-Time Setup Only)**

   Run the following command to initialize the project:

   ```bash
   python manage.py shell -c "from recommendations.tasks import update_district_weather_and_air_quality as ping; ping.delay()"
   ```

10. **Run the Development Server**

    ```bash
    python manage.py runserver
    ```

11. **Access the Application**  
    Open your browser and navigate to `http://127.0.0.1:8000`.

12. **Access API Documentation**  
    Open your browser and navigate to `http://127.0.0.1:8000/api/docs/`.

