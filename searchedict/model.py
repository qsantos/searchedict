# encoding: utf-8
from aqt import mw
from aqt.qt import *
from anki.notes import Note
from aqt.utils import showInfo, tooltip

from .edict.search import search_edict, search_enamdict
from .edict.deinflect import Deinflector


def check_field(model, config_key):
    try:
        model_field = mw.col.conf[config_key]
    except KeyError:
        return True
    if model_field is None:
        return True
    for field in model['flds']:
        if field['name'] == model_field:
            return True
    showInfo(u'Field "{}" not found'.format(model_field))
    return False


def note_set_field(note, config_key, value):
    try:
        model_field = mw.col.conf[config_key]
    except KeyError:
        return
    if model_field is None:
        return
    try:
        note[model_field] = value if value is not None else ''
    except KeyError:
        showInfo(f'Note type "{note.model()["name"]}" has not field /{model_field}"')


def add_notes(words):
    if not mw.col.conf.get(u'searchedict_hasopensettings'):
        showInfo(u'Please check the settings first')
        SettingsWindow.open()
        return

    # select deck
    deck_name = mw.col.conf.get('searchedict_deck')
    if deck_name is None:
        deck_id = mw.col.decks.selected()
    else:
        deck_id = mw.col.decks.id(deck_name)
    deck = mw.col.decks.get(deck_id)
    if deck is None:
        showInfo('Deck not found')
        return

    # select model
    try:
        model_name = mw.col.conf['searchedict_model']
    except KeyError:
        showInfo('Note type is not set')
        return
    model = mw.col.models.by_name(model_name)
    if model is None:
        showInfo('Note type not found')
        return
    model['did'] = deck['id']  # update model's default deck

    # check fields
    if not check_field(model, 'searchedict_kanjiField'):
        return
    if not check_field(model, 'searchedict_kanaField'):
        return
    if not check_field(model, 'searchedict_furiganaField'):
        return
    if not check_field(model, 'searchedict_definitionField'):
        return
    if not check_field(model, 'searchedict_idField'):
        return

    n_newcards = 0
    for word in words:
        # create new note
        note = Note(mw.col, model)
        # fill new note
        note_set_field(note, 'searchedict_kanjiField', word.kanji)
        note_set_field(note, 'searchedict_kanaField', word.kana)
        note_set_field(note, 'searchedict_furiganaField', word.get_furigana())
        note_set_field(note, 'searchedict_definitionField', word.get_meanings_html())
        note_set_field(note, 'searchedict_idField', word.get_sequence_number())

        # check for duplicates if id field is set
        idfield = mw.col.conf.get('searchedict_idField')
        if idfield is not None and mw.col.find_notes(f'{idfield}:{word.get_sequence_number()}'):
            continue

        # add card
        n_newcards += mw.col.addNote(note)
    mw.reset()
    tooltip(ngettext('{} card added.', '{} cards added.', n_newcards).format(n_newcards))


class WordSearchModel(QAbstractTableModel):
    def __init__(self):
        QAbstractTableModel.__init__(self)
        self.words = []

    def rowCount(self, index):
        return len(self.words)

    def columnCount(self, index):
        return 5

    def headerData(self, section, orientation, role):
        if orientation != Qt.Horizontal or role != Qt.DisplayRole:
            return QAbstractTableModel.headerData(self, section, orientation, role)
        return [
            "Kanji",
            "Kana",
            "Template",
            "JMDict ID",
            "Definition",
        ][section]

    def data(self, index, role):
        if not index.isValid():
            return
        if role == Qt.DisplayRole:
            word = self.words[index.row()]
            column = index.column()
            if column == 0:
                return word.kanji
            elif column == 1:
                return word.kana
            elif column == 2:
                return word.get_furigana()
            elif column == 3:
                return word.get_sequence_number()
            elif column == 4:
                return '\n'.join(word.get_meanings())
            else:
                raise NotImplemented
        else:
            return

    def sort(self, column, order):
        reverse = order == Qt.DescendingOrder
        if column == 0:
            key = lambda word: word.kanji
        elif column == 1:
            key = lambda word: word.kana
        else:
            return
        self.modelAboutToBeReset.emit()
        self.words = sorted(self.words, key=key, reverse=reverse)
        self.modelReset.emit()

    def search(self, word, enable_edict=True, enable_deinflect=False, enable_enamdict=False):
        self.modelAboutToBeReset.emit()
        self.words = []
        if enable_edict:
            if enable_deinflect:
                self.words += list(deinflector.search_edict(word))
            else:
                self.words += list(search_edict(word))
        if enable_enamdict:
            self.words += list(search_enamdict(word))
        self.modelReset.emit()


deinflector = Deinflector()
word_search = WordSearchModel()
