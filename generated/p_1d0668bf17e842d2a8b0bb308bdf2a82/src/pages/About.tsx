export default function About() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <section className="mb-12">
        <img
          src="https://picsum.photos/seed/hero-about/1200/700"
          alt="Elegant jewellery display"
          className="w-full h-auto rounded-lg shadow-lg"
        />
        <h1 className="text-4xl font-bold mt-6">About Us</h1>
        <p className="mt-4 text-lg text-gray-700">
          Welcome to our elegant and minimalistic jewellery store. We believe that simplicity is the ultimate sophistication, and our collection reflects that philosophy. Each piece is crafted with care and designed to enhance your natural beauty.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-3xl font-semibold mb-4">Our Collection</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-about-1/400/300"
              alt="Minimalist gold ring"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-xl font-medium">Gold Ring</h3>
              <p className="text-gray-600">$150</p>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-about-2/400/300"
              alt="Elegant silver necklace"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-xl font-medium">Silver Necklace</h3>
              <p className="text-gray-600">$200</p>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-about-3/400/300"
              alt="Stylish bracelet"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-xl font-medium">Stylish Bracelet</h3>
              <p className="text-gray-600">$120</p>
            </div>
          </div>
        </div>
      </section>

      <section className="text-center">
        <h2 className="text-3xl font-semibold mb-4">Join Our Community</h2>
        <p className="mb-6 text-lg text-gray-700">
          Sign up for our newsletter to receive exclusive offers and updates on our latest collections.
        </p>
        <button className="bg-black text-white py-2 px-4 rounded-lg hover:bg-gray-800 transition">
          Subscribe Now
        </button>
      </section>
    </div>
  );
}
