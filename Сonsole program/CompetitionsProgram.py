import time
import difflib as dl
import pathlib
import pandas as pd
import requests
from datetime import date
import datetime
from bs4 import BeautifulSoup


class HTMLTableParser(object):
    """
    This class is used to parse HTML as a string.
    It is having one main method.

    Methods
    -------
    parser_url():
        Read HTMl, parse it and return the result in one string.
    """

    @staticmethod
    def parser_url():
        """
        This method parse the HTML as a string
        with need table in there.
        :return: html after parsing as a string
        :rtype: NavigableString
        """

        response = requests.get('https://dance.vftsarr.ru/reg_module/?mode=reglists&competition_id=97')
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_competition = soup.find('table', class_='table')
            return list_of_competition
        else:
            print("Bad request.")  # Instead of exceptions.


class TableInformation(object):
    """
    This class is used to process data from HTML
    into pandas tables for comfort. They are divided into categories:
    a general table and a table with all participants.
    It is having three main methods.

    Methods
    -------
    links_to_table():
        Search for all category links in HTML and returns all participants.
    parser_links():
        Create a table with all participants.
    category_information():
        Create a table with all general data in HTML.
    """

    @staticmethod
    def links_to_table():
        """
        This method search all links in HTML and parse it as a string.
        :returns: all links in string and pandas table with participants.
        :rtype: list and DataFrame.
        """

        html_parser = HTMLTableParser()  # Object from method of different class.
        parse_main_table = html_parser.parser_url()

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
        if len(link_column_name) > 0 and \
                len(link_column_name) != n_link_column:
            raise Exception("Column titles do not match the number of columns")

        for link in link_url:
            response = requests.get(link)
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_participants = soup.find('table', class_='table')
            n_rows += len(list_of_participants.find_all('tr'))
            n_rows -= 1

        columns = link_column_name if len(link_column_name) > 0 \
            else range(0, n_link_column)
        participants = pd.DataFrame(columns=columns, index=range(1, (n_rows + 1)))

        return link_url, participants

    @staticmethod
    def parser_links():
        """
        This method add data to participants table.
        :return: pandas table with participants.
        :rtype: DataFrame.
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

        data_from_url = TableInformation()
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
        :return: pandas table with all general data in HTML.
        :rtype: DataFrame.
        """

        html_parser = HTMLTableParser()
        parse_main_table = html_parser.parser_url()

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
        links_data = data_from_url.parser_links()

        file_ext = r"*.xlsx"
        path = list(pathlib.Path().glob(file_ext))

        # First parse two need table.
        length = len(path)
        df = pd.ExcelFile(path[length - 1])
        if length == 0:
            print("Excel file not found. Please upload file to the folder.")  # Instead of exception.
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
    It is having tree main methods.!!!

    Methods
    -------
    save_result_of_matching():
        Create Excel table with results.
    match_results():
        Match new results with past.
    save_coloured_table():
        Save result of matching last results.
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

        # TODO: Find right contact
        contacts = []
        for one in list_with_contacts['Контакт']:
            contacts.append(one)

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
        today = str(datetime.datetime.today().strftime("%d-%m-%Y_%H.%M.%S"))
        result = pd.DataFrame(data)

        """pair_from_file = []
        for one in list_with_contacts['Пара']:
            pair_from_file.append(one)

        count = 0
        count_list = []
        for one in pair_from_file:
            cross = dl.get_close_matches(one, pairs, n=1, cutoff=0.9)
            count += 1
            if len(cross) > 0:
                count_list.append(count)

        contact_names = []
        for one in count_list:
            one_contact = list_with_contacts.loc[one // 2, 'Контакт']
            contact_names.append(one_contact)

        a = b = c = 0
        new_contacts = []
        for one in range(len(contact_names)):
            b += one
            while c != b:
                new_contacts.append(contact_names[a])
                c += 1
            a += 1
        result.insert(4, 'Контакт', new_contacts)"""
        # TODO: красиво сохранять excel
        end = result.style.set_properties(**{'text-align': 'right'})
        print('The results save in file Result_', today, '.xlsx\n')
        end.to_excel('Result_' + today + '.xlsx')
        return result

    @staticmethod
    def match_results():
        """
        This method is match the last result and second-to-last result,
        and paints the cell blue.
        :return: Coloured table with match.
        :rtype: DataFrame
        """

        save_class = SaveResultsInTable()
        result_of_matching = save_class.save_result_of_matching()
        last = result_of_matching  # The last file.

        file_ext = r"*.xlsx"
        path = list(pathlib.Path().glob(file_ext))
        length = len(path)
        df = pd.ExcelFile(path[length - 3])
        second_to_last = df.parse()  # The past file, before last.
        # TODO: разобрать на пары и сравнивать, если нашёл то, что не было, то раскрасить и сохранить
        count = 0
        for one in last:
            cross = dl.get_close_matches(one, second_to_last, n=1, cutoff=0.9)
            if len(cross) == 0:
                count += 1
                last.style.apply('background-color: SkyBlue')

        return last, count

    # TODO: make so that methods call each other
    @staticmethod
    def save_coloured_table():
        """
        This method save result of matching last results.
        :return: None
        """

        save_class = SaveResultsInTable()
        result_of_matching = save_class.match_results()
        last, count = result_of_matching  # The last file with marks.

        new = len(last['Пара']) - count // 2
        print('There were matches with the previous file:', count,
              'and', new, 'new ones.')
        answer = input('Do you want to save the matching results to a Excel file?\n'
                       'Answers: yes or no.')
        today = str(datetime.datetime.today().strftime("%d-%m-%Y_%H.%M.%S"))
        if answer == 'yes':
            last.to_excel('Matching' + today + '.xlsx')


class StartingConsole(object):
    """
    This class is have to use program from console
    and print information about program's work.
    It is having two main methods.

    Methods
    -------
    greetings_farewell():
        Output a greeting and a farewell.
    out_results():
        Outputs the main information of competition and events,
        and the result of the matched participants from file.
    """

    @staticmethod
    def greetings_farewell():
        """
        This method outputs a greeting and a farewell.
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

        # Calling the basic information from another method.
        console_class = StartingConsole()
        console_class.out_results()

        # Need to output the information about matches of participants.
        matching_data = Matcher()
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

        # Save results of matching.
        save_class = SaveResultsInTable()
        save_class.save_result_of_matching()

        # Farewell.
        print(shift * 18, "That's all information.\n", shift * 20, "Have a nice day!\n")

    @staticmethod
    def out_results():
        """
        This method outputs the main information of competition and events,
        and the result of the matched participants from file.
        :return: None.
        """

        steaks = '-' * 63
        shift = ' '

        # Processing the information about competitions.
        data_from_url = TableInformation()
        all_table_data = data_from_url.category_information()
        inform_category = all_table_data

        # Find the nearest dates and names of competitions.
        date_now = str(date.today()).replace('-', ',').split(',')
        year = date_now[0]
        month = date_now[1]
        day = date_now[2]
        to_day = ''.join(day + '.' + month).split()

        date_after = []
        category_after = []
        for one in inform_category['Дата']:
            if str(to_day) <= one:
                date_after.append(one)  # Nearest dates after today.
        for one in inform_category[inform_category['Дата'].isin(date_after)]['Категория']:
            category_after.append(one)  # Names of "after today" competitions.

        # Output the information about today's date
        # and nearest competitions with date.
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


if __name__ == "__main__":
    sc = StartingConsole()
    sc.greetings_farewell()
    
    
