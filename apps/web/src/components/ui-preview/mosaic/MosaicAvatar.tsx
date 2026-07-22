import { avatarTone, initials, type AvatarTone } from './demo-data';

type Props = {
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  tone?: AvatarTone;
};

export function MosaicAvatar({ name, size = 'md', tone }: Props) {
  const t = tone ?? avatarTone(name);
  return (
    <span className={`mosaic-avatar mosaic-avatar--${size} mosaic-avatar--${t}`} aria-hidden>
      {initials(name)}
    </span>
  );
}
