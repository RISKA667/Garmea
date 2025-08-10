import React from 'react';

const Card = ({ 
  children, 
  title, 
  subtitle, 
  variant = 'default', 
  className = '', 
  headerAction,
  footer,
  ...props 
}) => {
  const baseClasses = 'bg-white rounded-xl border border-gray-200 overflow-hidden';
  
  const variants = {
    default: 'shadow-soft',
    elevated: 'shadow-medium',
    prominent: 'shadow-large',
    flat: 'shadow-none'
  };
  
  const classes = `${baseClasses} ${variants[variant]} ${className}`;
  
  return (
    <div className={classes} {...props}>
      {(title || subtitle || headerAction) && (
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-gray-900">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-sm text-gray-600 mt-1">
                  {subtitle}
                </p>
              )}
            </div>
            {headerAction && (
              <div>
                {headerAction}
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="px-6 py-4">
        {children}
      </div>
      
      {footer && (
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50">
          {footer}
        </div>
      )}
    </div>
  );
};

export default Card; 