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
                className={`[padding:6px_12px]! ${currentPage <= 1 ? "[opacity:0.5]!" : "[opacity:1]!"} ${currentPage <= 1 ? "[cursor:not-allowed]!" : "[cursor:pointer]!"}`}
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
                className={`[padding:6px_12px]! ${currentPage >= totalPages ? "[opacity:0.5]!" : "[opacity:1]!"} ${currentPage >= totalPages ? "[cursor:not-allowed]!" : "[cursor:pointer]!"}`}
            >
                Next
            </Button>
        </div>
    );
};

export default PaginationControls;
