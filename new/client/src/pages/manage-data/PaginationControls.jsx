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
        <div className="flex! justify-between! items-center! mt-[16px]! p-[16px_0]! [border-top:1px_solid_#e5e7eb]!">
            <Button 
                variant="ghost" type="submit" 
                disabled={currentPage <= 1} 
                onClick={() => onPageChange(currentPage - 1)}
                style={{ opacity: currentPage <= 1 ? 0.5 : 1, cursor: currentPage <= 1 ? 'not-allowed' : 'pointer', padding: '6px 12px' }}
            >
                Previous
            </Button>
            <span className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
                Page {currentPage} of {totalPages}
            </span>
            <Button 
                variant="ghost" type="submit" 
                disabled={currentPage >= totalPages} 
                onClick={() => onPageChange(currentPage + 1)}
                style={{ opacity: currentPage >= totalPages ? 0.5 : 1, cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer', padding: '6px 12px' }}
            >
                Next
            </Button>
        </div>
    );
};

export default PaginationControls;
