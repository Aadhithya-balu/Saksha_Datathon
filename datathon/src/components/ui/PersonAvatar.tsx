/**
 * Issue #107 — PersonAvatar
 *
 * Displays a person's image from the real database (image_url field).
 * Falls back to an initials badge when no image is available.
 * Never uses placeholder/stock images.
 */
import React, { useState } from 'react';
import { User } from 'lucide-react';

interface PersonAvatarProps {
  imageUrl?: string | null;
  name: string;
  /** Size in pixels (applied as width & height). Default: 80 */
  size?: number;
  /** Extra Tailwind classes for the outer container */
  className?: string;
  /** Accent colour for the initials fallback border/text */
  accentColor?: string;
  /** Shape: 'square' (rounded-lg) or 'circle' (rounded-full). Default: 'square' */
  shape?: 'square' | 'circle';
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export const PersonAvatar: React.FC<PersonAvatarProps> = ({
  imageUrl,
  name,
  size = 80,
  className = '',
  accentColor = '#1E6FD9',
  shape = 'square',
}) => {
  const [imgError, setImgError] = useState(false);
  const [imgLoading, setImgLoading] = useState(true);

  const shapeClass = shape === 'circle' ? 'rounded-full' : 'rounded-lg';
  const hasImage = imageUrl && !imgError;

  return (
    <div
      className={`relative overflow-hidden shrink-0 flex items-center justify-center ${shapeClass} ${className}`}
      style={{
        width: size,
        height: size,
        background: hasImage ? 'transparent' : 'var(--bg-secondary, #0d1526)',
        border: `1px solid ${accentColor}30`,
      }}
      aria-label={`Profile image for ${name}`}
    >
      {hasImage && (
        <>
          {imgLoading && (
            <div
              className={`absolute inset-0 ${shapeClass} animate-pulse`}
              style={{ background: 'var(--bg-tertiary, #111d35)' }}
            />
          )}
          <img
            src={imageUrl}
            alt={`Photo of ${name}`}
            className={`w-full h-full object-cover object-center ${shapeClass}`}
            onLoad={() => setImgLoading(false)}
            onError={() => { setImgError(true); setImgLoading(false); }}
            draggable={false}
          />
        </>
      )}

      {!hasImage && (
        <div className="flex flex-col items-center justify-center w-full h-full gap-0.5">
          {name ? (
            <span
              className="font-mono font-bold select-none leading-none"
              style={{
                fontSize: Math.max(10, size * 0.28),
                color: accentColor,
              }}
            >
              {getInitials(name)}
            </span>
          ) : (
            <User
              style={{ width: size * 0.45, height: size * 0.45, color: accentColor, opacity: 0.5 }}
              strokeWidth={1.5}
            />
          )}
          <span
            className="font-mono uppercase tracking-widest select-none"
            style={{ fontSize: Math.max(5, size * 0.09), color: `${accentColor}70` }}
          >
            No image
          </span>
        </div>
      )}
    </div>
  );
};

export default PersonAvatar;
