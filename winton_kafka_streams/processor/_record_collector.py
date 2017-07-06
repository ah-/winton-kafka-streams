"""
Record collector sends produced results to kafka topic

"""

import time

from .serde.identity import IdentitySerde
from .._error import KafkaStreamsError

class DefaultStreamPartitioner:
    def __init__(self):
        pass

    def partition(self):
        return 0

class RecordCollector:
    """
    Collects records to be output to Kafka topics after
    they have been processed by the topology

    """
    def __init__(self, _producer):
        self.producer = _producer

    def send_to_stream(self, topic, key, value, timestamp, keySerialiser, valueSerialiser,
                       *, stream_partitioner = DefaultStreamPartitioner()):

        partitions = producer.partitionsFor(topic)
        n_partitions = len(partitions)
        if n_partitions == 0:
            raise KafkaStreamsError(f"Could not get partition information for {topic}." \
                                    "This can happen if the topic does not exist.")

        self.send_to_partition(topic, key, value, timestamp, keySerialiser,
                               valueSerialiser, partition = partitioner.partition(key, value, n_partitions))

    def send_to_partition(self, topic, key, value, timestamp,
                          keySerialiser = IdentitySerde(), valueSerialiser = IdentitySerde(), *, partition = 0):
        key = keySerialiser.serialise(key)
        value = valueSerialiser.serialise(value)
        produced = False
        while not produced:
            try:
                self.producer.produce(topic, value, key, partition, self.on_delivery, timestamp)
                self.producer.poll(0) # Ensure previous message's delivery reports are served
                produced = True
            except BufferError as be:
                log.exception(be)
                self.producer.poll(10) # Wait a bit longer to give buffer more time to flush
            except NotImplementedError as nie:
                log.exception(nie)
                produced = True  # should not enter infinite loop

    def on_delivery(self, err, msg):
        """
        Callback function after a value is output to a source.

        Will raise an exception if an error is detected.

        TODO: Decide if an error should be raised or if this should be demoted?
              Can an error be raised if a broker fails? Should we simply warn
              and continue to poll and retrty in this case?
        """

        # TODO: Is err correct? Should we check if msg has error?
        if err:
            raise KafkaStreamsError(f'Error on delivery of message {msg}')

    def flush(self):
        """
        Flush all pending items in the queue to the output topic on Kafka

        """
        log.debug('Flushing producer')
        self.producer.flush()

    def close(self):
        log.debug('Closing producer')
        self.producer.close()
