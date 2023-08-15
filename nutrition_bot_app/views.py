import requests
from django.http import JsonResponse

def get_calories(query):
    api_url = 'https://api.api-ninjas.com/v1/nutrition?query={}'.format(query)
    response = requests.get(api_url, headers={'X-Api-Key': 'qISGbWJ9OZTV9EjZwGz/Yw==7fDtHz92e655T987'})
    if response.status_code == requests.codes.ok:
        calories = response.json()[0]['calories']
        return calories
    else:
        return "Error: {} - {}".format(response.status_code, response.text)

def calculate_calories(request):
    if request.method == 'POST':
        data = request.POST
        query = data.get('query')
        calories = get_calories(query)
        return JsonResponse({'calories': calories})
    else:
        return JsonResponse({'error': 'Invalid request method'})
