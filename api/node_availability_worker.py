import threading
import queue
from sqlalchemy.orm import sessionmaker


node_availability_queue = queue.Queue()
node_availability_batch_size = 20


# process_node_availabilities processes node availability data
# in batches and inserts to db. This work happens in a separate thread.
def process_node_availabilities(db_engine, availabilities_queue):
    session_factory = sessionmaker(bind=db_engine)

    batch = []
    db_session = None
    while True:
        try:
            item = availabilities_queue.get()
            batch.append(item)
            if len(batch) >= node_availability_batch_size:
                db_session = session_factory()
                db_session.bulk_save_objects(batch)
                db_session.commit()
                batch = []
                print("Committed node availability batch")
                return
        except Exception as e:
            print("Failed to process node availabilities:", e)
            if db_session is not None:
                db_session.rollback()
        finally:
            if db_session is not None:
                db_session.close()


def start_node_availability_worker(db_engine, availabilities_queue):
    x = threading.Thread(target=process_node_availabilities, args=(db_engine, availabilities_queue))
    x.start()
