import time
import difflib as dl
import pathlib
import pandas as pd
import requests
from datetime import date
import datetime
from bs4 import BeautifulSoup


class MainSiteParser(object):
    """
    This class is used to parse HTML from main site.
    It is having four main methods.

    Methods
    -------
    parse_website():
        Read HTMl, parse it and
        return two parameters (start and end of the month).
    find_all_on_line_register():
        Collect all links with online registration.
    use_data_main_site():
        Collect the information about events and
        save links to participants category.
    one_site():
        This method search all links in registration and parse it as a string.
    """

    @staticmethod
    def parse_website():
        """
        This method parse the HTML from main site
        at the beginning and end of the month.

        :return start_part, end_part: two HTMl at the beginning and end of the month.
        :rtype: NavigableString
        """
        to_day = date.today()  # Find date values that need to search.
        today_month = to_day.strftime('%m')
        today_year = to_day.strftime('%Y')
        end_date = to_day + datetime.timedelta(days=28)  # Short February.
        end_month = end_date.strftime('%m')
        end_year = end_date.strftime('%Y')

        from_url = f'https://dance.vftsarr.ru/index.php?id=2&type=0&Show_Month=' \
                   f'{today_month}&Show_Year={today_year}'
        to_url = f'https://dance.vftsarr.ru/index.php?id=2&type=0&Show_Month=' \
                 f'{end_month}&Show_Year={end_year}'

        from_response = requests.get(from_url)
        to_response = requests.get(to_url)
        if from_response.status_code == 200 and to_response.status_code == 200:
            from_soup = BeautifulSoup(from_response.content, 'html.parser')
            to_soup = BeautifulSoup(to_response.content, 'html.parser')
            start_part = from_soup.find('tbody')
            end_part = to_soup.find('tbody')
            return start_part, end_part
        else:
            print("Bad request.")  # Instead of exceptions.

    @staticmethod
    def find_all_on_line_register():
        """
        This method collects all links with online registration.

        :return tr_tags: The list with registration links.
        :rtype: list
        """
        main_parser = MainSiteParser()
        parser_urls = main_parser.parse_website()
        start_part, end_part = parser_urls

        to_day = date.today()
        end_date = to_day + datetime.timedelta(days=28)

        tr_tags = []
        for one in start_part.find_all('tr'):
            if one.select('a[href^="https://dance.vftsarr.ru/reg_module/"]') and \
                    (one.find('td', class_="MY").get_text(separator='.') >= to_day.strftime('%d.%m.%Y')):
                tr_tags.append(one)
        for one in end_part.find_all('tr'):
            if one.select('a[href^="https://dance.vftsarr.ru/reg_module/"]') and \
                    (one.find('td', class_="MY").get_text(separator='.') <= end_date.strftime('%d.%m.%Y')):
                tr_tags.append(one)
        return tr_tags

    @staticmethod
    def use_data_main_site():
        """
        This method gets information about the event
        and saves links registration categories.

        :return main_table: The table with information.
        :rtype: DataFrame
        """
        main_parser = MainSiteParser()
        find_tags = main_parser.find_all_on_line_register()
        tr_tags = find_tags

        dates = []
        name = []
        city_organizes = []
        online_register = []
        for one in tr_tags:
            dates.append(one.find('td', class_="MY").get_text(separator='.'))
            name.append(one.select_one('td > font[size="1"]').get_text(separator='\n')
                        + '\n' + one.select_one('td > font[size="2"]').get_text(separator='\n'))
            city_organizes.append(one.find('td', valign="top").get_text(separator='\n'))
            online_register.append(one.select_one(
                'a[href^="https://dance.vftsarr.ru/reg_module/"]')['href'])

        def multiple_replace(target_str, replace_values):
            """
            This method changes the value in links to lists with participants.

            :param target_str: the string to change.
            :param replace_values: changed values in the form of "key - value".
            :return target_str: the string after change.
            :rtype: str
            """
            for word, changed in replace_values.items():
                target_str = str(target_str).replace(word, changed)
            return target_str

        values = {'?mode=registration&competition': '?mode=reglists&competition',
                  '?competition': '?mode=reglists&competition', "'": "", "[": "", "]": ""}
        on_register = multiple_replace(online_register, values)
        online_register = on_register.split(', ')

        data = {"Дата": dates, "Соревнование": name,
                "Город, организатор": city_organizes, "Регистрация": online_register}
        main_table = pd.DataFrame(data).drop_duplicates(keep='first')
        return main_table

    @staticmethod
    def one_site():
        """
        This method search all links in registration and parse it as a string.

        :return list_of_competition: list with links.
        :rtype: list.
        """

        main_parser = MainSiteParser()
        main_table = main_parser.use_data_main_site()

        list_of_competition = []
        for one in main_table['Регистрация']:
            response = requests.get(one)
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_competition.append(soup.find('table', class_='table'))
        return list_of_competition

# TODO heck... That needs to fix after main site rewrite ↓↓↓


class TableInformation(object):
    """
    This class is used to process data from HTML into pandas tables.
    They are divided into categories: a general table and a table
    with all participants.
    It is having four main methods.

    Methods
    -------
    links_to_table():
        Search for all category links in HTML and returns all participants.
    parser_links():
        Create a table with all participants.
    category_in_links():
       Add column category to table participants.
    category_information():
        Create a table with all general data in HTML.
    """

    @staticmethod
    def links_to_table():
        """
        This method search all links in HTML and parse it as a string.

        :returns link_url: all links in string.
        :return participants: pandas table with participants.
        :rtype: list, DataFrame.
        """
        html_parser = MainSiteParser()
        parse_main_table = html_parser.one_site()

        link_column_name = []
        n_link_column = 0
        n_rows = 0

        # Search and save all links with information in category and parse it.
        link_url = []
        a_tags = parse_main_table.find_all('a', href=True)
        for link in a_tags:
            link_url.append(link['href'])
        response = requests.get(link_url[0])
        soup = BeautifulSoup(response.content, 'html.parser')
        list_of_participants = soup.find('table', class_='table')

        # Handle column names when find them.
        th_tags = list_of_participants.find_all('th', scope='col')
        n_link_column += len(th_tags)
        if len(th_tags) > 0 and len(link_column_name) == 0:
            for th in th_tags:
                link_column_name.append(th.get_text())

        # Save column titles.
        for link in link_url:
            response = requests.get(link)
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_participants = soup.find('table', class_='table')
            n_rows += (len(list_of_participants.find_all('tr')) - 1)
        columns = link_column_name if len(link_column_name) > 0 \
            else range(0, n_link_column)
        participants = pd.DataFrame(columns=columns, index=range(1, (n_rows + 1)))
        return link_url, participants

    @staticmethod
    def parser_links():
        """
        This method add data to participants table.

        :return participants: pandas table with participants.
        :return number: number of category.
        :rtype: DataFrame, list
        """

        data_from_url = TableInformation()
        data_from_links = data_from_url.links_to_table()
        link_url, participants = data_from_links

        # Download data to Excel table from links.
        number = []
        row_number = 0
        for link in link_url:
            response = requests.get(link)
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_participants = soup.find('table', class_='table')
            number.append(len(list_of_participants.find_all('th', scope='row')) / 4)
            for row in list_of_participants.find_all('tr'):
                column_number = 0
                columns = row.find_all('th', scope='row')
                for br in soup.find_all('br'):
                    br.replace_with("%s\n" % br.text)
                for column in columns:
                    participants.iat[row_number, column_number] = column.get_text().strip()
                    column_number += 1
                if len(columns) > 0:
                    row_number += 1

        return participants, number

    @staticmethod
    def category_in_links():
        """
        This method add column category to table participants.

        :return participants: pandas table with participants.
        :rtype: DataFrame.
        """

        data_from_url = TableInformation()
        parse_participants = data_from_url.parser_links()
        participants, number = parse_participants

        all_table_data = data_from_url.category_information()
        category_name = []
        for one in all_table_data['Категория']:
            category_name.append(one)

        a = b = c = 0
        new_category = []
        for one in number:
            b += one
            while c != b:
                new_category.append(category_name[a])
                c += 1
            a += 1
        participants.insert(4, 'Категория', new_category)

        return participants

    @staticmethod
    def category_information():
        """
        This method create a new table of all general data from HTML.

        :return all_category: pandas table with all general data in HTML.
        :rtype: DataFrame.
        """

        html_parser = MainSiteParser()
        parse_main_table = html_parser.one_site()

        # Find number of rows and columns. And find the columns titles.
        n_columns = len(parse_main_table.find_all('th', scope='col')) - 1  # Set the number of columns for table.
        n_rows = len(parse_main_table.find_all('th', scope='row'))  # Determine the number of rows in the table.
        column_names = []

        # Handle column names when find them.
        th_tags = parse_main_table.find_all('th', scope='col')
        if len(th_tags) > 0 and len(column_names) == 0:
            for th in th_tags:
                column_names.append(th.get_text())
        del column_names[0]

        # Save column titles.
        if len(column_names) > 0 and len(column_names) != n_columns:
            print("Column titles do not match the number of columns.")  # Instead of exception.

        columns = column_names if len(column_names) > 0 \
            else range(0, n_columns)
        all_category = pd.DataFrame(columns=columns, index=range(1, n_rows + 1))
        all_category.index.names = [parse_main_table.find('th', scope='col').text]
        row_marker = 0
        for row in parse_main_table.find_all('tr'):
            column_marker = 0
            columns = row.find_all('td')
            for column in columns:
                all_category.iat[row_marker, column_marker] = column.get_text().strip()
                column_marker += 1
            if len(columns) > 0:
                row_marker += 1

        return all_category


class Matcher(object):
    """
    This class is used to match data from HTML and data from user's file.
    It is having two main methods.

    Methods
    -------
    data_for_match():
        Collect data for matching.
    find_match():
        Search matches in files and save them.
    """

    @staticmethod
    def data_for_match():
        """
        This method collects data for matching.
        :return: data about participants in user's file and HTML,
                and data from all links.
        :rtype: list.
        """

        data_from_url = TableInformation()
        links_data = data_from_url.category_in_links()

        # First parse two need table.
        df = pd.ExcelFile('База клиентов.xlsx')
        if df == 0:
            print(" Excel file not found."  # Instead of exception.
                  " Please upload file to the folder or change name of the file.")
        list_to_match = df.parse()
        list_of_participants = links_data

        # Uploading the list of participants.
        participants_in_links = []
        for one in list_of_participants['Участники']:
            participants_in_links.append(one)
        participants_in_links = ' '.join(participants_in_links).strip().split()

        participants_in_file = []
        for one in list_to_match['Пара']:
            participants_in_file.append(one)
        participants_in_file = ' '.join(participants_in_file).replace('-', '').strip().split()

        return participants_in_links, participants_in_file, list_of_participants

    @staticmethod
    def find_match():
        """
        This method search all matches in tables (with mistakes to) and save it.
        :return: matching results and list of categories.
        :rtype: list.
        """

        matching_data = Matcher()
        data_match = matching_data.data_for_match()
        participants_in_links, participants_in_file, list_of_participants = data_match

        # Make a list of each participant, regardless of the pair.
        i = 1
        links_participants = []
        while i - 1 != len(participants_in_links):
            name = participants_in_links[i - 1] + " " + participants_in_links[i]
            links_participants.append(name)
            i += 2

        i = 1
        file_participants = []
        while i - 1 != len(participants_in_file):
            name = participants_in_file[i - 1] + " " + participants_in_file[i]
            file_participants.append(name)
            i += 2

        category_in_links = []
        for one in list_of_participants['Категория']:
            category_in_links.append(one)

        # Search and saving matches.
        results = []
        count = 0
        count_list = []
        for name in links_participants:
            cross = dl.get_close_matches(name, file_participants, n=1, cutoff=0.9)
            count += 1
            if len(cross) > 0:
                results.append(name)
                count_list.append(count)

        category_names = []
        for one in count_list:
            category = list_of_participants.loc[one // 2, 'Категория']
            category_names.append(category)

        return results, category_names


class SaveResultsInTable(object):
    """
    This class is used to save results of parsing im Excel table,
    and match new results with past.
    It is having two main methods.

    Methods
    -------
    save_result_of_matching():
        Create Excel table with results.
    match_results():
        Match new results with past.
    """

    @staticmethod
    def save_result_of_matching():
        """
        This method create Excel table with results.
        :return: table with the result of the match.
        :rtype: DataFrame.
        """

        matching_data = Matcher()
        matching_search = matching_data.find_match()
        single, category_name = matching_search

        file_ext = r"*.xlsx"
        path = list(pathlib.Path().glob(file_ext))
        length = len(path)
        df = pd.ExcelFile(path[length - 1])
        list_with_contacts = df.parse()

        pairs = []
        category = []
        x = 1
        while (x - 1) != len(single):
            one_pair = "".join(single[x-1] + " - " + single[x])
            one_category = "".join(category_name[x-1])
            pairs.append(one_pair)
            category.append(one_category)
            x += 2

        data = {'Пара': pairs, 'Категория': category}  # Add 'Контакты': contacts
        result = pd.DataFrame(data)
        end_result = result.merge(list_with_contacts, how='left', left_on='Пара', right_on='Пара')
        return end_result


class StartingConsole(object):
    """
    This class is have to use program from console
    and print information about program's work.
    It is having three main methods.

    Methods
    -------
    greetings():
        Output a greeting and a farewell.
    out_results():
        Outputs the main information of competition and events,
        and the result of the matched participants from file.
    farewell():
        Ends the console program and outputs a goodbye.
    """

    @staticmethod
    def greetings():
        """
        This method outputs a greeting.
        :return: None.
        """

        # Output the greeting.
        steaks = '-' * 63
        shift = ' '

        print("\n", shift * 25, "Hello!\n"
              " This program shows information about the nearest competitions\n",
              shift * 9, "and matches with the list of participants.")
        print(steaks, end='\n')
        time.sleep(2)

        console_class = StartingConsole()
        console_class.out_results()  # The basic information from another method.

        matching_data = Matcher()  # Output the information about matches.
        matching_search = matching_data.find_match()

        new_results, new_category = matching_search
        count_results = len(new_results)
        if count_results > 0:
            print(f" By file found {count_results // 2} matches:\n"
                  " Pairs:", shift * 34, "Category:")
            one = 1
            while one - 1 != count_results:
                print(shift * 5, "-", new_results[one - 1], "и", new_results[one],
                      shift * ((len(new_results[(one - 2)]) + len(new_results[(one - 3)])) - 18),
                      " -", new_category[one - 1], end='\n')
                one += 2
        else:
            print("\n There are no matches found.\n")
        print(steaks, end='\n')
        time.sleep(2)

        console_class = StartingConsole()
        console_class.farewell()

    @staticmethod
    def out_results():
        """
        This method outputs the main information of competition and events,
        and the result of the matched participants from file.
        :return: None.
        """

        steaks = '-' * 63
        shift = ' '

        data_from_url = TableInformation()  # The information about competitions.
        all_table_data = data_from_url.category_information()
        inform_category = all_table_data

        # Find the nearest dates and names of competitions.
        date_now = str(date.today()).replace('-', ',').split(',')
        year = date_now[0]
        month = date_now[1]
        day = date_now[2]
        today = ''.join(day + '.' + month).split()

        date_after = []
        category_after = []
        for one in inform_category['Дата']:
            if str(today) <= one:
                date_after.append(one)  # Nearest dates after today.
        for one in inform_category[inform_category['Дата'].isin(date_after)]['Категория']:
            category_after.append(one)  # Names of "after today" competitions.

        # Output the information about the nearest competitions with date.
        print(f" Today's date: {day}.{month}.{year}.\n")
        if len(date_after) > 0:
            print(" The nearest upcoming competitions:\n"
                  " Date:          Category:")
            one = 0
            while one != len(date_after):
                print(shift * 5, "-", date_after[one], shift * 11,
                      "-", category_after[one], end='\n')
                one += 1
        else:
            print(" There are no upcoming competitions.")
        print(steaks, end='\n')

    @staticmethod
    def farewell():
        """
        This method ends the console program and outputs a goodbye.
        :return: None
        """

        shift = ' '

        save_class = SaveResultsInTable()  # Save results of matching.
        saved_result = save_class.save_result_of_matching()
        end_result = saved_result

        today = str(datetime.datetime.today().strftime("%d-%m-%Y_%H.%M.%S"))
        end = end_result.style.set_properties(**{'text-align': 'right'})
        print(' The results save in file Result_', today, '.xlsx\n')
        end.to_excel('Result_' + today + '.xlsx')

        print(shift * 18, "That's all information.\n", shift * 20,
              "Have a nice day!\n")  # Farewell.


if __name__ == "__main__":
    sc = StartingConsole()
    sc.greetings()
