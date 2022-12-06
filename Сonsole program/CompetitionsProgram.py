import time
import difflib as dl
import pathlib
import pandas as pd
import requests
from datetime import date
from bs4 import BeautifulSoup


class HTMLTableParser(object):
    """
    This class is having one main method.
    It parses HTML as a string.
    """

    @staticmethod
    def parser_url():
        """
        This method parse the HTML as a string
        and search need table in there.
        """

        response = requests.get('https://dance.vftsarr.ru/reg_module/?mode=reglists&competition_id=97')
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_competition = soup.find('table', class_='table')
            return list_of_competition
        else:
            raise Exception("Bad request.")


class TableInformation(object):
    """
    This class is having two main methods.
    It parses HTML as a string.
    Then convert this into Excel table.
    In the end, it matches data from HTML
    and data from user's file.
    """

    @staticmethod
    def parser_links():
        """
        This method search all links in HTML
        and return information of category in table.
        """

        hp = HTMLTableParser()  # object from method of different class
        pu = hp.parser_url()

        link_column_name = []
        n_link_column = 0
        n_rows = 0

        """
        Search and save all links 
        with information in category and parse it.
        """

        link_url = []
        a_tags = pu.find_all('a', href=True)
        for link in a_tags:
            link_url.append(link['href'])

        response = requests.get(link_url[0])
        soup = BeautifulSoup(response.content, 'html.parser')
        list_of_participants = soup.find('table', class_='table')

        """
        Handle column names when find them.
        """

        th_tags = list_of_participants.find_all('th', scope='col')
        n_link_column += len(th_tags)
        if len(th_tags) > 0 and len(link_column_name) == 0:
            for th in th_tags:
                link_column_name.append(th.get_text())

        """
        Save column titles.
        """

        if len(link_column_name) > 0 and \
                len(link_column_name) != n_link_column:
            raise Exception("Column titles do not match the number of columns")

        for link in link_url:
            response = requests.get(link)
            soup = BeautifulSoup(response.content, 'html.parser')
            list_of_participants = soup.find('table', class_='table')
            n_rows += len(list_of_participants.find_all('tr'))
            n_rows -= 1

        """
        Download data to Excel table from links.
        """

        number = []
        columns = link_column_name if len(link_column_name) > 0 \
            else range(0, n_link_column)
        participants = pd.DataFrame(columns=columns, index=range(1, (n_rows + 1)))
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

        ti = TableInformation()
        ci = ti.category_information()

        category_name = []
        for one in ci['Категория']:
            category_name.append(one)

        i = u = x = 0
        new_category = []
        for one in number:
            u += one
            while x != u:
                new_category.append(category_name[i])
                x += 1
            i += 1
        participants.insert(4, 'Категория', new_category)

        return participants

    @staticmethod
    def category_information():
        """
        This method create a new table of data from HTML.
        """

        hp = HTMLTableParser()  # object from method of different class
        pu = hp.parser_url()

        """
        Find number of rows and columns. 
        And find the columns titles.
        """

        n_columns = len(pu.find_all('th', scope='col')) - 1  # Determine the number of rows in the table.
        n_rows = len(pu.find_all('th', scope='row'))  # Set the number of columns for table.
        column_names = []

        """
        Handle column names when find them.
        """

        th_tags = pu.find_all('th', scope='col')
        if len(th_tags) > 0 and len(column_names) == 0:
            for th in th_tags:
                column_names.append(th.get_text())
        del column_names[0]

        """
        Save column titles.
        """

        if len(column_names) > 0 and \
                len(column_names) != n_columns:
            raise Exception(
                "Column titles do not match "
                "the number of columns."
            )

        columns = column_names if len(column_names) > 0 \
            else range(0, n_columns)
        all_category = pd.DataFrame(columns=columns, index=range(1, n_rows + 1))
        all_category.index.names = [pu.find('th', scope='col').text]
        row_marker = 0
        for row in pu.find_all('tr'):
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
    This class is having one main method.
    It matches data from HTML and data from user's file.
    """

    @staticmethod
    def find_match():
        """
        This method search all matches
        (with mistakes to) and show it.
        """

        ti = TableInformation()
        pl = ti.parser_links()

        file_ext = r"*.xlsx"
        path = list(pathlib.Path().glob(file_ext))

        """
        First parse two need table.
        """
        if len(path) != 0:
            df = pd.ExcelFile(path[0])
        else:
            raise Exception("Excel file not found. "
                            "Please upload file to the folder.")
        list_to_match = df.parse()
        list_of_participants = pl

        """
        Uploading the list of participants.
        """

        participants_in_links = []
        for one in list_of_participants['Участники']:
            participants_in_links.append(one)
        participants_in_links = ' '.join(participants_in_links).strip().split()

        participants_in_file = []
        for one in list_to_match['Пара']:
            participants_in_file.append(one)
        participants_in_file = ' '.join(participants_in_file).replace('-', '').strip().split()

        """
        Make a list of each participant, 
        regardless of the pair.
        """

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

        """
        Search and saving matches.
        """

        results = []
        count = 0
        count_list = []
        for name in links_participants:
            x = dl.get_close_matches(name, file_participants, n=1, cutoff=0.9)
            count += 1
            if len(x) > 0:
                results.append(name)
                count_list.append(count)

        category_names = []
        for one in count_list:
            cat = list_of_participants.loc[one // 2, 'Категория']
            category_names.append(cat)

        return results, category_names


class StartingConsole(object):
    """
    This class is having !!SOME!! main methods.
    It allows to use program from console
    and print information about program's work.
    """

    @staticmethod
    def out_results():
        """
        This method outputs the main information
        of competition and events. And the result of
        the matched participants from file.
        """

        """
        Output the greeting.
        """

        steaks = '-' * 63
        print()
        print("\n                         Hello!\n"
              " This program shows information about the nearest competitions\n"
              "         and matches with the list of participants.")
        print(steaks, end='\n')
        time.sleep(2)

        """
        Output the information about competitions.
        """

        ti = TableInformation()
        ci = ti.category_information()
        inform_category = ci

        """
        Find the nearest dates 
        and names of competitions.
        """

        date_now = str(date.today()).replace('-', ',').split(',')
        year = date_now[0]
        month = date_now[1]
        day = date_now[2]
        to_day = ''.join(day + '.' + month).split()

        date_before = []
        date_after = []
        count = 3
        for one in inform_category['Дата']:
            if str(to_day) >= one:
                date_before.append(one)  # three nearest dates before today
            while count != 0:
                if str(to_day) <= one:
                    date_after.append(one)  # three nearest dates after today
                count -= 1
        del date_before[0:(len(date_before) - 3)]

        category_before = []
        category_after = []
        for one in inform_category[inform_category.Дата.isin(date_before)]['Категория']:
            category_before.append(one)
        del category_before[0:(len(category_before) - 3)]  # names of "before today" competitions

        for one in inform_category[inform_category.Дата.isin(date_after)]['Категория']:
            category_after.append(one)
        del category_after[3: len(category_after)]  # names of "after today" competitions

        """
        Output the information about today's date
        and nearest competitions with date.
        """

        print(f" Today's date: {day}.{month}.{year}.\n")
        if len(date_before) > 0:
            print(" The nearest past competitions:\n"
                  " Date:          Category:")
            one = 0
            while one != len(date_before):
                print("     -", date_before[one], "           -", category_before[one], end='\n')
                one += 1
        else:
            print("\n There are no past competitions.")

        if len(date_after) > 0:
            print(" The nearest upcoming competitions:\n"
                  " Date:          Category:")
            one = 0
            while one != len(date_after):
                print("     -", date_after[one], "           -", category_after[one], end='\n')
                one += 1
        else:
            print("\n There are no upcoming competitions.")
        print(steaks, end='\n')

        """
        Need to output the information 
        about matches of participants.
        """

        shift = ' '

        ma = Matcher()
        fm = ma.find_match()

        new_results, new_category = fm
        count_res = len(new_results)
        if count_res > 0:
            print(f" By file found {count_res//2} matches:\n"
                  " Pairs:", shift*34, "Category:")
            one = 1
            while one-1 != count_res:
                print("     -", new_results[one-1], "и", new_results[one],
                      shift*((len(new_results[(one-2)])+len(new_results[(one-3)]))-18),
                      " -", new_category[one-1], end='\n')
                one += 2
        else:
            print("\n There are no matches found.\n")
        print(steaks, end='\n')
        time.sleep(2)

        """
        Farewell.
        """

        print(shift*18, "That's all information.\n", shift*20, "Have a nice day!\n")


if __name__ == "__main__":
    sc = StartingConsole()
    sc.out_results()
