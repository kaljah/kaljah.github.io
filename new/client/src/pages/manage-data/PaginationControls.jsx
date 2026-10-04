import React, { useEffect } from 'react';
import { Button } from "../../ui";

const PaginationControls = ({ currentPage, totalItems, itemsPerPage, onPageChange }) => {
    const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage) || 1);

    useEffect(() => {
        if (currentPage > totalPages && totalPages > 0) {
            onPageChange(totalPages);
        }
    }, [currentPage, totalPages, onPageChange]);

    return (
        <div className="mt-4 flex items-center justify-between border-t border-border py-4">
            <Button variant="ghost" size="sm" disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1)}>
                Previous
            </Button>
            <span className="text-sm text-text-secondary">
                Page {currentPage} of {totalPages}
            </span>
            <Button variant="ghost" size="sm" disabled={currentPage >= totalPages} onClick={() => onPageChange(currentPage + 1)}>
                Next
            </Button>
        </div>
    );
};

export default PaginationControls;
