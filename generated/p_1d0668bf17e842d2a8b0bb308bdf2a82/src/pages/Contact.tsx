export default function Contact() {
  return (
    <div className="flex flex-col items-center p-6 bg-gray-50">
      <section className="w-full mb-12">
        <img
          src="https://picsum.photos/seed/hero-contact/1200/700"
          alt="Elegant jewelry display"
          className="w-full h-64 object-cover rounded-lg shadow-lg"
        />
      </section>
      <section className="w-full max-w-4xl mb-12 text-center">
        <h1 className="text-3xl font-bold text-gray-800">Get in Touch</h1>
        <p className="mt-4 text-gray-600">
          We would love to hear from you! Whether you have a question about our products, pricing, or anything else, our team is ready to answer all your questions.
        </p>
      </section>
      <section className="w-full max-w-4xl mb-12">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Our Products</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-contact-1/400/300"
              alt="Minimalist ring"
              className="w-full h-32 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Minimalist Ring</h3>
              <p className="text-gray-500">$199</p>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-contact-2/400/300"
              alt="Elegant necklace"
              className="w-full h-32 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Elegant Necklace</h3>
              <p className="text-gray-500">$299</p>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <img
              src="https://picsum.photos/seed/card-contact-3/400/300"
              alt="Stylish bracelet"
              className="w-full h-32 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Stylish Bracelet</h3>
              <p className="text-gray-500">$149</p>
            </div>
          </div>
        </div>
      </section>
      <section className="w-full max-w-4xl text-center">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Contact Us</h2>
        <p className="text-gray-600 mb-4">Fill out the form below to reach us:</p>
        <form className="flex flex-col items-center">
          <input
            type="text"
            placeholder="Your Name"
            className="mb-4 p-2 border border-gray-300 rounded w-80"
            required
          />
          <input
            type="email"
            placeholder="Your Email"
            className="mb-4 p-2 border border-gray-300 rounded w-80"
            required
          />
          <textarea
            placeholder="Your Message"
            className="mb-4 p-2 border border-gray-300 rounded w-80 h-32"
            required
          />
          <button
            type="submit"
            className="bg-gray-800 text-white py-2 px-4 rounded hover:bg-gray-700 transition"
          >
            Send Message
          </button>
        </form>
      </section>
    </div>
  );
}
