import datetime
from random import randrange

import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from config import user_token, comm_token, offset, line
from database import *


class VKBot:
    def __init__(self):
        print('Bot was created')
        self.vk = vk_api.VkApi(token=comm_token)
        self.longpoll = VkLongPoll(self.vk)

    def write_msg(self, user_id, message):
        self.vk.method('messages.send', {'user_id': user_id,
                                         'message': message,
                                         'random_id': randrange(10 ** 7)})

    def get_params(self, add_params: dict = None):
        params = {
            'access_token': user_token,
            'v': '5.131'
        }
        if add_params:
            params.update(add_params)
            pass
        return params

    def name(self, user_id):
        response = requests.get(
            'https://api.vk.com/method/users.get',
            self.get_params({'user_ids': user_id})
        )
        try:
            for user_info in response.json()['response']:
                first_name = user_info['first_name']
                last_name = user_info['last_name']
                return first_name, last_name
        except:
            print(f"Не удалось получить имя пользователя для {user_id}: {response.json()['error']['error_msg']}")
            self.write_msg(user_id, 'Ошибка с нашей стороны. Попробуйте позже.')
            return False

    def get_info(self, user_id):
        response = requests.get(
            'https://api.vk.com/method/users.get',
            self.get_params({'user_ids': user_id,
                             'fields': 'bdate,sex'}))
        resp = response.json()['response']
        return resp

    def get_sex(self, resp):
        for i in range(resp):
            if i.get('sex') == 2:
                sex = 1
                return sex
            elif i.get('sex') == 1:
                sex = 2
                return sex

    def get_age_low(self, user_id, resp):
        for i in resp:
            date = i.get('bdate')
            date_list = date.split('.')
            if len(date_list) == 3:
                year = int(date_list[2])
                year_now = int(datetime.date.today().year)
                return year_now - year
            elif len(date_list) == 2 or date not in resp:
                self.write_msg(user_id, 'Введите нижний порог возраста (min - 16): ')
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                        age = event.text
                        return age

    def get_age_high(self, user_id, resp):
        for i in resp:
            date = i.get('bdate')
            date_list = date.split('.')
            if len(date_list) == 3:
                year = int(date_list[2])
                year_now = int(datetime.date.today().year)
                return year_now - year
            elif len(date_list) == 2 or date not in resp:
                self.write_msg(user_id, 'Введите верхний порог возраста (max - 65): ')
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                        age = event.text
                        return age

    def find_city(self, user_id, resp):
        for i in resp:
            if i.get('city') != 0:
                city = (i.get('id'))
                return city
            elif 'city' not in i:
                self.write_msg(user_id, 'Введите название вашего города: ')
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                        city = event.text(user_id)
                        if city != '' or city is not None:
                            return city

    def find_user(self, user_id):
        """ПОИСК ЧЕЛОВЕКА ПО ПОЛУЧЕННЫМ ДАННЫМ"""
        url = f'https://api.vk.com/method/users.search'
        params = {'access_token': user_token,
                  'v': '5.131',
                  'sex': self.get_sex(user_id),
                  'age_from': self.get_age_low(user_id),
                  'age_to': self.get_age_high(user_id),
                  'city': self.find_city(user_id),
                  'fields': 'is_closed, id, first_name, last_name',
                  'status': '1' or '6',
                  'count': 500}
        resp = requests.get(url, params=params)
        resp_json = resp.json()
        dict_1 = resp_json['response']
        try:
            list_1 = dict_1['items']
            for person_dict in list_1:
                if person_dict.get('is_closed') == False:
                    first_name = person_dict.get('first_name')
                    last_name = person_dict.get('last_name')
                    vk_id = str(person_dict.get('id'))
                    vk_link = 'vk.com/id' + str(person_dict.get('id'))
                    insert_data_users(first_name, last_name, vk_id, vk_link)
                else:
                    continue
            return f'Поиск завершён'
        except KeyError:
            self.write_msg(user_id, 'Ошибка получения токена')

    def find_persons(self):
        self.write_msg(self.found_person_info())
        self.person_id()
        insert_data_seen_users(self.person_id(), offset)  # offset
        self.get_photos(self.person_id())
        self.send_photo('Лучшие фото')

    def found_person_info(self):
        tuple_person = select(offset)
        list_person = []
        for i in tuple_person:
            list_person.append(i)
        return f'{list_person[0]} {list_person[1]}, ссылка - {list_person[3]}'

    def person_id(self):
        tuple_person = select(offset)
        list_person = []
        for i in tuple_person:
            list_person.append(i)
            return str(list_person[2])

    def get_photos(self, user_id):
        url = 'https://api.vk.com/method/photos.getAll'
        params = {'access_token': user_token,
                  'type': 'album',
                  'owner_id': user_id,
                  'extended': 1,
                  'count': 25,
                  'v': '5.131'}
        resp = requests.get(url, params=params).json()
        dict_photos = {}

        try:
            popular_pics = sorted(
                resp['response']['items'],
                key=lambda k: k['likes']['count'] + k['comments']['count'],
                reverse=True
            )[0:3]
            for pic in popular_pics:
                if 'owner_id' not in dict_photos.keys():
                    dict_photos['owner_id'] = pic['owner_id']
                    dict_photos['pics_ids'] = []
                dict_photos['pics_ids'].append(pic['id'])

        except KeyError:
            pass

        finally:
            return dict_photos

    def send_photo(self, user_id, message):
        self.vk.method('messages.send', {'user_id': user_id,
                                         'access_token': user_token,
                                         'message': message,
                                         'attachment': f'photo{self.person_id()}_{self.get_photos(self.person_id())}',
                                         'random_id': 0})



bot = VKBot()
