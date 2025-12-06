"""Treasury management for Agent Hive - tracking revenue, costs, and profitability."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging
import sqlite3
import threading

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Types of financial transactions."""

    REVENUE = "revenue"
    COST = "cost"
    REFUND = "refund"
    INVESTMENT = "investment"


@dataclass
class Transaction:
    """A financial transaction record."""

    transaction_id: str
    transaction_type: TransactionType
    amount: float
    source: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type.value,
            "amount": self.amount,
            "source": self.source,
            "description": self.description,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return cls(
            transaction_id=data["transaction_id"],
            transaction_type=TransactionType(data["transaction_type"]),
            amount=data["amount"],
            source=data["source"],
            description=data["description"],
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


class Treasury:
    """
    Treasury for the Agent Hive.

    Manages all financial operations:
    - Revenue tracking from products/services
    - Cost tracking from operations
    - Profitability analysis
    - Budget allocation

    Uses SQLite for persistence with thread-safe access.
    """

    def __init__(self, db_path: str = "data/treasury.db"):
        """
        Initialize the treasury.

        Args:
            db_path: Path to SQLite database for persistence
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self._initialize_db()
        logger.info(f"Treasury initialized at {self.db_path}")

    def _initialize_db(self) -> None:
        """Initialize the SQLite database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id TEXT PRIMARY KEY,
                        transaction_type TEXT NOT NULL,
                        amount REAL NOT NULL,
                        source TEXT NOT NULL,
                        description TEXT,
                        metadata TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_type ON transactions(transaction_type)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp)
                """)
                conn.commit()
            finally:
                conn.close()

    def record_transaction(self, transaction: Transaction) -> str:
        """
        Record a financial transaction.

        Args:
            transaction: Transaction to record

        Returns:
            Transaction ID
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO transactions
                    (transaction_id, transaction_type, amount, source, description, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        transaction.transaction_id,
                        transaction.transaction_type.value,
                        transaction.amount,
                        transaction.source,
                        transaction.description,
                        json.dumps(transaction.metadata),
                        transaction.timestamp,
                    ),
                )
                conn.commit()
                logger.debug(
                    f"Recorded {transaction.transaction_type.value}: "
                    f"${transaction.amount:.2f} from {transaction.source}"
                )
                return transaction.transaction_id
            finally:
                conn.close()

    def add_revenue(
        self,
        amount: float,
        source: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record revenue.

        Args:
            amount: Revenue amount
            source: Source of revenue (product, service, etc.)
            description: Description of the revenue
            metadata: Additional metadata

        Returns:
            Transaction ID
        """
        import uuid

        transaction = Transaction(
            transaction_id=str(uuid.uuid4())[:8],
            transaction_type=TransactionType.REVENUE,
            amount=amount,
            source=source,
            description=description,
            metadata=metadata or {},
        )
        return self.record_transaction(transaction)

    def add_cost(
        self,
        amount: float,
        source: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a cost.

        Args:
            amount: Cost amount
            source: Source of cost (LLM calls, tools, etc.)
            description: Description of the cost
            metadata: Additional metadata

        Returns:
            Transaction ID
        """
        import uuid

        transaction = Transaction(
            transaction_id=str(uuid.uuid4())[:8],
            transaction_type=TransactionType.COST,
            amount=amount,
            source=source,
            description=description,
            metadata=metadata or {},
        )
        return self.record_transaction(transaction)

    def get_total_revenue(self, since: Optional[str] = None) -> float:
        """Get total revenue, optionally since a timestamp."""
        return self._get_total_by_type(TransactionType.REVENUE, since)

    def get_total_costs(self, since: Optional[str] = None) -> float:
        """Get total costs, optionally since a timestamp."""
        return self._get_total_by_type(TransactionType.COST, since)

    def get_profit(self, since: Optional[str] = None) -> float:
        """Get profit (revenue - costs), optionally since a timestamp."""
        revenue = self.get_total_revenue(since)
        costs = self.get_total_costs(since)
        return revenue - costs

    def _get_total_by_type(
        self, transaction_type: TransactionType, since: Optional[str] = None
    ) -> float:
        """Get total amount for a transaction type."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                if since:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount), 0)
                        FROM transactions
                        WHERE transaction_type = ? AND timestamp >= ?
                    """,
                        (transaction_type.value, since),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount), 0)
                        FROM transactions
                        WHERE transaction_type = ?
                    """,
                        (transaction_type.value,),
                    )
                result = cursor.fetchone()
                return result[0] if result else 0.0
            finally:
                conn.close()

    def get_transactions(
        self,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Get transactions, optionally filtered.

        Args:
            transaction_type: Filter by type
            limit: Maximum number of transactions
            since: Filter by timestamp

        Returns:
            List of transactions
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                query = "SELECT * FROM transactions WHERE 1=1"
                params = []

                if transaction_type:
                    query += " AND transaction_type = ?"
                    params.append(transaction_type.value)

                if since:
                    query += " AND timestamp >= ?"
                    params.append(since)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                transactions = []
                for row in rows:
                    transactions.append(
                        Transaction(
                            transaction_id=row[0],
                            transaction_type=TransactionType(row[1]),
                            amount=row[2],
                            source=row[3],
                            description=row[4],
                            metadata=json.loads(row[5]) if row[5] else {},
                            timestamp=row[6],
                        )
                    )
                return transactions
            finally:
                conn.close()

    def get_revenue_by_source(self, since: Optional[str] = None) -> Dict[str, float]:
        """Get revenue breakdown by source."""
        return self._get_breakdown_by_source(TransactionType.REVENUE, since)

    def get_costs_by_source(self, since: Optional[str] = None) -> Dict[str, float]:
        """Get costs breakdown by source."""
        return self._get_breakdown_by_source(TransactionType.COST, since)

    def _get_breakdown_by_source(
        self, transaction_type: TransactionType, since: Optional[str] = None
    ) -> Dict[str, float]:
        """Get breakdown by source for a transaction type."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                if since:
                    cursor.execute(
                        """
                        SELECT source, SUM(amount)
                        FROM transactions
                        WHERE transaction_type = ? AND timestamp >= ?
                        GROUP BY source
                    """,
                        (transaction_type.value, since),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT source, SUM(amount)
                        FROM transactions
                        WHERE transaction_type = ?
                        GROUP BY source
                    """,
                        (transaction_type.value,),
                    )
                return dict(cursor.fetchall())
            finally:
                conn.close()

    def get_financial_summary(self) -> Dict[str, Any]:
        """Get comprehensive financial summary."""
        revenue = self.get_total_revenue()
        costs = self.get_total_costs()
        profit = revenue - costs
        margin = profit / revenue if revenue > 0 else 0.0

        return {
            "total_revenue": revenue,
            "total_costs": costs,
            "profit": profit,
            "profit_margin": margin,
            "revenue_by_source": self.get_revenue_by_source(),
            "costs_by_source": self.get_costs_by_source(),
            "transaction_count": self._get_transaction_count(),
        }

    def _get_transaction_count(self) -> int:
        """Get total number of transactions."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM transactions")
                result = cursor.fetchone()
                return result[0] if result else 0
            finally:
                conn.close()
