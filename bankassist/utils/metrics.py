"""Time-series metrics collection for services."""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict
import time


class MetricsCollector:
    """Collects time-series metrics for graphing."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.max_datapoints = 1000  # Keep last 1000 data points per metric
    
    def increment(self, metric_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        self.counters[metric_name] += value
        self._add_datapoint(metric_name, value, "counter", tags)
    
    def gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric (current value)."""
        self.gauges[metric_name] = value
        self._add_datapoint(metric_name, value, "gauge", tags)
    
    def timing(self, metric_name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timing metric."""
        self._add_datapoint(metric_name, duration_ms, "timing", tags)
    
    def _add_datapoint(self, metric_name: str, value: float, metric_type: str, tags: Dict[str, str] = None):
        """Add a datapoint to the time-series."""
        datapoint = {
            "timestamp": time.time(),
            "value": value,
            "type": metric_type,
            "tags": tags or {}
        }
        self.metrics[metric_name].append(datapoint)
        
        # Trim old datapoints
        if len(self.metrics[metric_name]) > self.max_datapoints:
            self.metrics[metric_name] = self.metrics[metric_name][-self.max_datapoints:]
    
    def get_metric_data(self, metric_name: str, time_period_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metric data for a specific time period."""
        if metric_name not in self.metrics:
            return []
        
        cutoff_time = time.time() - (time_period_minutes * 60)
        return [
            dp for dp in self.metrics[metric_name]
            if dp["timestamp"] >= cutoff_time
        ]
    
    def get_all_metrics(self, time_period_minutes: int = 60) -> Dict[str, Any]:
        """Get all metrics for dashboard."""
        result = {
            "service": self.service_name,
            "timestamp": time.time(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "time_series": {}
        }
        
        for metric_name in self.metrics:
            result["time_series"][metric_name] = self.get_metric_data(metric_name, time_period_minutes)
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "service": self.service_name,
            "total_metrics": len(self.metrics),
            "total_counters": len(self.counters),
            "total_gauges": len(self.gauges),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges)
        }
