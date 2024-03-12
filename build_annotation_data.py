'''
build_annotation_data.py

Builds annotation data in a JSON format suitable for the FrameNet web app.

@date: 2024-02-14
@author: Dmetri Hayes/Nimkiins MikZaabii
'''
import mariadb
import sys
import os
import json

DIR = '/WHEREVER/anno-data'

# hard-coded constants for database fetching
UNANN_ID = 1
MANUAL_ID = 2
STATUS_DICT = {UNANN_ID: 'UNANN', MANUAL_ID: 'MANUAL'}
LAYER_TYPES_DICT = {1: 'FE', 2: 'Target', 3: 'GF', 4: 'PT', 10: 'BNC', 12: 'PENN', 15: 'SCPOS', 22: 'HEPPLE'}
POS_LAYER_IDS = [10, 12, 15, 22]
LAYER_TYPES = list(LAYER_TYPES_DICT.keys())
# LAYER_TYPES_STR = ', '.join([str(k) for k in LAYER_TYPES]) # necessary for use in 
ITYPE_DICT = {1: 'Normal', 2: 'APos', 3: 'CNI', 4: 'DNI', 5: 'INI', 6: 'INC'}


def connect_to_mariadb():
   # Connect to MariaDB Platform
  try:
      conn = mariadb.connect(
          user="USER",
          host="HOST",
          port=3306,
          database="fn2b"
      )
  except mariadb.Error as e:
      print(f"Error connecting to MariaDB Platform: {e}")
      sys.exit(1)
  return conn

def create_lu_anno_json(lu_id, cur, dir):
  # step 1: get the LU's annotation set info
  # filter to only UNANN and MANUAL annotation
  cur.execute('SELECT ID, Sentence_Ref, SubCorpus_Ref, CurrentAnnoStatus_Ref FROM AnnotationSet WHERE LexUnit_Ref=? AND CurrentAnnoStatus_Ref = 2', (lu_id, ))
  annosets_info = cur.fetchall()
  # step 2: get the subcorpus information
  cur.execute('SELECT ID, Name FROM SubCorpus WHERE LexUnit_Ref = {}'.format(lu_id))
  subcorpus_info = cur.fetchall()
  subcorpus_to_name = {info[0] : info[1] for info in subcorpus_info}

  # step 3: get the sentence info
  #  create a mapping from sentence id to info
  sent_to_info = {}
  # match the subcorpus to the sentences
  subcorpus_to_sents = {}
  for _, sent_id, subcorpus_id, _ in annosets_info[:]:
      cur.execute('SELECT Text FROM Sentence WHERE ID=?', (sent_id, ))
      text = cur.fetchone()[0]
      sent_to_info[sent_id] = {'ID': sent_id, 'text': text, 'anno_sets': []}
      subcorpus_name = subcorpus_to_name[subcorpus_id]
      if subcorpus_name not in subcorpus_to_sents:
          subcorpus_to_sents[subcorpus_name] = []
      subcorpus_to_sents[subcorpus_name].append(sent_id)
      # step 4: find the UNANN annotation sets that are attached to the sentence
      cur.execute('SELECT ID, Sentence_Ref, SubCorpus_Ref, CurrentAnnoStatus_Ref FROM AnnotationSet WHERE Sentence_Ref=? AND CurrentAnnoStatus_Ref = 1', (sent_id, ))
      result = cur.fetchall()
      if len(result) == 0:
          raise ValueError('UNANN layer not found for sentence {}'.format(sent_id))
      # append to annosets_info
      annosets_info.extend(result)

  # TODO: consider caching data from the MiscLabel and FrameElement tables
  lu_data = {}
  cur.execute('SELECT SenseDesc, Lemma_Ref, Frame_Ref, Name FROM LexUnit WHERE ID = {}'.format(lu_id))

  definition, _, frameID, lu_name = cur.fetchone()
  lu_data['definition'] = definition
  lu_data['frameID'] = frameID
  lu_data['name'] = lu_name
  lu_data['subcorpora'] = []

  for a_id, sent_id, _, status_id in annosets_info:
    # get the current sentence's data
    sent_data = sent_to_info[sent_id]
    # step 3: prepare the annotation sets
    # NOTE: here we should have one MANUAL and one UNANN annotation sets
    anno_sets = sent_data['anno_sets']
    a_set = {}
    a_set['status'] = STATUS_DICT[status_id]
    a_set['ID'] = a_id
    # step 4: get the layers' ids
    # HARD-CODING LayerTypeRef statement since I can't seem to inject the right SQL
    if status_id == MANUAL_ID:
      cur.execute('SELECT ID, LayerType_Ref FROM Layer WHERE AnnotationSet_Ref=? AND LayerType_Ref <= 4', (a_id, ))
    elif status_id == UNANN_ID:
      cur.execute('SELECT ID, LayerType_Ref FROM Layer WHERE AnnotationSet_Ref=? AND LayerType_Ref IN (10, 12, 15, 22)', (a_id, ))
    else:
        raise ValueError('Unexpected LayerStatus ID! Must be 2 (MANUAL)')
    layer_info = cur.fetchall()
    layers = []
    for lay_id, lay_type in layer_info:
        lay = {}
        lay['ID'] = lay_id
        lay_name = LAYER_TYPES_DICT[lay_type]
        lay['name'] = lay_name
        # step 5: get the labels
        cur.execute('SELECT LabelType_Ref, StartChar, EndChar, InstantiationType_Ref FROM Label WHERE Layer_Ref=?', (lay_id,))
        label_info = cur.fetchall()
        labels = []
        for lab_type, start, end, itype in label_info:
            lab = {}
            lab['start'] = start
            lab['end'] = end
            if status_id == MANUAL_ID:
              lab['itype'] = ITYPE_DICT[itype]
            # step 6: get the "item" name from the corresponding tables ("label" is already used)
            cur.execute('SELECT DBTableName, DBTableID FROM LabelType WHERE ID=?', (lab_type, ))
            item_table_name, item_table_id = cur.fetchone()
            cur.execute('SELECT Name FROM {} WHERE ID=?'.format(item_table_name), (item_table_id, ))
            item_name = cur.fetchone()[0]
            lab['name'] = item_name
            labels.append(lab)
        lay['labels'] = labels
        layers.append(lay)
    a_set['layers'] = layers
    anno_sets.append(a_set)
    # d['anno_sets'] = anno_sets
    # anno_data.append(d)

  # finally, link the subcorpora to the sentences
  for name, sent_ids in subcorpus_to_sents.items():
      subcorpus_data = {}
      subcorpus_data['name'] = name
      subcorpus_data['sents'] = []
      for id in sent_ids:
          subcorpus_data['sents'].append(sent_to_info[id])
      lu_data['subcorpora'].append(subcorpus_data)

  # step 7: save to file
  with open(os.path.join(dir, '{}.json'.format(lu_id)), 'w') as f:
    json.dump(lu_data, f)
  print('COMPLETED LU {} ({})'.format(lu_id, lu_name))

def build_all_anno_data(cur, dir):
  # CREATE THE ANNOTATION DATA FOR ALL THE LUS
  cur.execute('SELECT ID FROM LexUnit')
  for x in cur.fetchall():
    create_lu_anno_json(x[0], cur, dir)

def build_frame_anno_data(frame_id, cur, dir):
   cur.execute('SELECT ID FROM LexUnit Where Frame_Ref = ?', (frame_id, ))
   for x in cur.fetchall():
      create_lu_anno_json(x[0], cur, dir)

conn = connect_to_mariadb()
# get cursor
cur = conn.cursor()

# build_all_anno_data(cur)

conn.close() 