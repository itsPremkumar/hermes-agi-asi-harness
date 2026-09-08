"""
MessageBus - Inter-agent communication via pub/sub pattern.

Provides a message passing system that supports:
- Topic-based publish/subscribe
- Pattern-based subscriptions (wildcards)
- Message history per topic
- Synchronous and asynchronous message delivery
- Message filtering
- Priority queues
"""

from __future__ import annotations

import fnmatch
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from queue import PriorityQueue, Empty


@dataclass(order=True)
class Message:
    """Represents a message on the bus."""
    priority: int
    topic: str = field(compare=False)
    data: Any = field(compare=False)
    sender: Optional[str] = field(default=None, compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass(order=True)
class Subscription:
    """A subscription to a topic pattern."""
    priority: int
    callback: Callable = field(compare=False)
    pattern: Optional[str] = field(default=None, compare=False)
    filter_fn: Optional[Callable[[Message], bool]] = field(default=None, compare=False)


class MessageBus:
    """Inter-agent message bus with pub/sub pattern."""

    def __init__(self, max_history_per_topic: int = 100):
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._pattern_subscriptions: List[Subscription] = []
        self._history: Dict[str, List[Message]] = defaultdict(list)
        self._max_history = max_history_per_topic
        self._lock = threading.RLock()
        self._running = False
        self._queue: PriorityQueue = PriorityQueue()
        self._delivery_thread: Optional[threading.Thread] = None

    def subscribe(
        self,
        topic: str,
        callback: Callable[[Message], Any],
        priority: int = 0,
        filter_fn: Optional[Callable[[Message], bool]] = None,
    ) -> Callable[[Message], Any]:
        """Subscribe to a specific topic. Returns callback for decorator use."""
        with self._lock:
            sub = Subscription(
                priority=priority, callback=callback, filter_fn=filter_fn
            )
            self._subscriptions[topic].append(sub)
            self._subscriptions[topic].sort(reverse=True)
        return callback

    def subscribe_decorator(
        self,
        topic: str,
        priority: int = 0,
    ) -> Callable[[Callable[[Message], Any]], Callable[[Message], Any]]:
        """Return a decorator that subscribes to a topic."""
        def decorator(fn: Callable[[Message], Any]) -> Callable[[Message], Any]:
            self.subscribe(topic, fn, priority=priority)
            return fn
        return decorator

    def subscribe_pattern(
        self,
        pattern: str,
        callback: Callable[[Message], Any],
        priority: int = 0,
        filter_fn: Optional[Callable[[Message], bool]] = None,
    ) -> Callable[[Message], Any]:
        """Subscribe to topics matching a glob pattern."""
        with self._lock:
            sub = Subscription(
                priority=priority,
                callback=callback,
                pattern=pattern,
                filter_fn=filter_fn,
            )
            self._pattern_subscriptions.append(sub)
            self._pattern_subscriptions.sort(reverse=True)
        return callback

    def unsubscribe(
        self,
        topic: str,
        callback: Optional[Callable[[Message], Any]] = None,
    ) -> bool:
        """Unsubscribe from a topic. If callback is None, remove all for topic."""
        with self._lock:
            if topic not in self._subscriptions:
                return False
            if callback is None:
                del self._subscriptions[topic]
                return True
            subs = self._subscriptions[topic]
            original_len = len(subs)
            self._subscriptions[topic] = [
                s for s in subs if s.callback is not callback
            ]
            return len(self._subscriptions[topic]) < original_len

    def unsubscribe_pattern(
        self,
        callback: Callable[[Message], Any],
    ) -> bool:
        """Unsubscribe a pattern-based callback."""
        with self._lock:
            original_len = len(self._pattern_subscriptions)
            self._pattern_subscriptions = [
                s for s in self._pattern_subscriptions if s.callback is not callback
            ]
            return len(self._pattern_subscriptions) < original_len

    def publish(
        self,
        topic: str,
        data: Any = None,
        sender: Optional[str] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Publish a message to a topic."""
        msg = Message(
            priority=priority,
            topic=topic,
            data=data,
            sender=sender,
            metadata=metadata or {},
        )

        with self._lock:
            # Store in history
            self._history[topic].append(msg)
            if len(self._history[topic]) > self._max_history:
                self._history[topic] = self._history[topic][-self._max_history :]

            # Collect matching subscriptions
            subs = list(self._subscriptions.get(topic, []))
            pattern_subs = [
                s
                for s in self._pattern_subscriptions
                if s.pattern and fnmatch.fnmatch(topic, s.pattern)
            ]

        # Deliver to specific subscribers
        for sub in subs:
            if sub.filter_fn and not sub.filter_fn(msg):
                continue
            try:
                sub.callback(msg)
            except Exception:
                pass

        # Deliver to pattern subscribers
        for sub in pattern_subs:
            if sub.filter_fn and not sub.filter_fn(msg):
                continue
            try:
                sub.callback(msg)
            except Exception:
                pass

        return msg

    def publish_async(
        self,
        topic: str,
        data: Any = None,
        sender: Optional[str] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Queue a message for async delivery."""
        msg = Message(
            priority=priority,
            topic=topic,
            data=data,
            sender=sender,
            metadata=metadata or {},
        )
        self._queue.put(msg)

    def start_async(self) -> None:
        """Start the async delivery thread."""
        self._running = True
        self._delivery_thread = threading.Thread(
            target=self._delivery_loop, daemon=True
        )
        self._delivery_thread.start()

    def stop_async(self) -> None:
        """Stop the async delivery thread."""
        self._running = False
        if self._delivery_thread:
            self._delivery_thread.join(timeout=5.0)
            self._delivery_thread = None

    def get_topics(self) -> Set[str]:
        """Get all topics with subscribers or history."""
        with self._lock:
            topics = set(self._subscriptions.keys()) | set(self._history.keys())
            return topics

    def get_subscribers(self, topic: str) -> int:
        """Get the number of subscribers for a topic."""
        with self._lock:
            count = len(self._subscriptions.get(topic, []))
            count += sum(
                1
                for s in self._pattern_subscriptions
                if s.pattern and fnmatch.fnmatch(topic, s.pattern)
            )
            return count

    def get_history(
        self, topic: str, limit: int = 100
    ) -> List[Message]:
        """Get message history for a topic."""
        with self._lock:
            return list(self._history.get(topic, []))[-limit:]

    def clear_history(self, topic: Optional[str] = None) -> None:
        """Clear message history. If topic is None, clear all."""
        with self._lock:
            if topic:
                self._history.pop(topic, None)
            else:
                self._history.clear()

    def remove_all_subscribers(self, topic: Optional[str] = None) -> None:
        """Remove all subscribers for a topic, or all topics if None."""
        with self._lock:
            if topic:
                self._subscriptions.pop(topic, None)
            else:
                self._subscriptions.clear()
                self._pattern_subscriptions.clear()

    def _delivery_loop(self) -> None:
        """Background thread for async message delivery."""
        while self._running:
            try:
                msg = self._queue.get(timeout=0.1)
                self.publish(
                    topic=msg.topic,
                    data=msg.data,
                    sender=msg.sender,
                    priority=msg.priority,
                    metadata=msg.metadata,
                )
            except Empty:
                continue
            except Exception:
                pass
