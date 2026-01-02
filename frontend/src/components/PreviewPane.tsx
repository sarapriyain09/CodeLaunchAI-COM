type Props = {
  url?: string | null;
};

export default function PreviewPane({ url }: Props) {
  return (
    <iframe title="Preview" src={url ?? "about:blank"} className="w-full h-full border-0" />
  );
}
