import time
from config import user_token, comm_token, offset, line
import vk_api
import requests
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randrange
from database import insert_data_users, select, insert_data_seen_users


class VKBot:
    def __init__(self):
        print('Bot was created')
        self.vk = vk_api.VkApi(token=comm_token)
        self.longpoll = VkLongPoll(self.vk)

    def write_msg(self, user_id, message):
        self.vk.method('messages.send', {'user_id': user_id,
                                         'message': message,
                                         'random_id': randrange(10 ** 7)})

    def name(self, user_id):
        url = f'https://api.vk.com/method/users.get'
        params = {'access_token': user_token,
                  'user_ids': user_id,
                  'v': '5.131'}
        repl = requests.get(url, params=params)
        response = repl.json()
        try:
            information_dict = response['response']
            for i in information_dict:
                for key, value in i.items():
                    first_name = i.get('first_name')
                    return first_name
        except KeyError:
            self.write_msg(user_id, 'Ошибка получения токена, введите токен в переменную - user_token')


    def get_user_info(self, user_id):
        try:
            fields = """
            sex, bdate, city
            """

            params = {
                'user_ids': user_id,
                'access_token': user_token,
                'fields': fields,
                'v': '5.131'
            }

            resp_url = f'https://api.vk.com/method/users.get'
            resp = requests.get(resp_url, params).json()

            return resp['response'][0]

        except IndexError:
            return False

        except KeyError:
            return False

    def get_sex(self, resp):
        information_list = resp['response']
        for i in information_list:
            if i.get('sex') == 2:
                find_sex = 1
                return find_sex
            elif i.get('sex') == 1:
                find_sex = 2
                return find_sex

    def get_age(self, resp):
        information_list = resp['response']
        for i in information_list:
            bdate = i.get('bdate').split('.')
            age = int(time.strftime('%Y')) - int(bdate[-1])
            age_from = str(age - 3)
            age_to = str(age + 3)
            return {'age_from': age_from, 'age_to': age_to}

    def find_city(self, user_id, resp):
        information_dict = resp['response']
        for i in information_dict:
                if 'city' in i:
                    city = i.get('city')
                    id = str(city.get('id'))
                    return id
                elif 'city' not in i:
                    self.write_msg(user_id, 'Введите название вашего города: ')
                    for event in self.longpoll.listen():
                        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                            city_name = event.text
                            id_city = city_name(user_id, city_name)
                            if id_city != '' or id_city != None:
                                return str(id_city)
                            else:
                                break

    def find_user(self, user_id):
        url = f'https://api.vk.com/method/users.search'
        params = {'access_token': user_token,
                  'v': '5.131',
                  'sex': self.get_sex(user_id),
                  'age_from': self.get_age(user_id)['age_from'],
                  'age_to': self.get_age(user_id)['age_to'],
                  'city': self.find_city(user_id),
                  'fields': 'is_closed, id, first_name, last_name',
                  'status': '1' or '6',
                  'count': 500}
        resp = requests.get(url, params=params)
        resp_json = resp.json()
        try:
            dict_1 = resp_json['response']
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
            return False

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


    def send_photo(self, user_id, message, offset):
        self.vk.method('messages.send', {'user_id': user_id,
                                         'access_token': user_token,
                                         'message': message,
                                         'attachment': f'photo{self.person_id(offset)}_{self.get_photos(self.person_id(offset))}',
                                         'random_id': 0})


    def find_persons(self, user_id, offset):
        self.write_msg(user_id, self.found_person_info(offset))
        self.person_id(offset)
        insert_data_seen_users(self.person_id(offset), offset)  # offset
        self.get_photos(self.person_id(offset))
        self.send_photo(user_id, 'Лучшие фото', offset)


    def found_person_info(self, offset):
        tuple_person = select(offset)
        list_person = []
        for i in tuple_person:
            list_person.append(i)
        return f'{list_person[0]} {list_person[1]}, ссылка - {list_person[3]}'

    def person_id(self, offset):
        tuple_person = select(offset)
        list_person = []
        for i in tuple_person:
            list_person.append(i)
        return str(list_person[2])


bot = VKBot()


