export default function Home() {
  return (
    <div className="flex flex-col items-center bg-gray-50">
      <header className="w-full bg-white shadow">
        <div className="max-w-6xl mx-auto p-6">
          <h1 className="text-3xl font-bold text-center text-gray-800">Elegant Jewelry</h1>
        </div>
      </header>
      
      <section className="w-full">
        <img 
          src="https://picsum.photos/seed/hero-home/1200/700" 
          alt="Elegant jewelry display" 
          className="w-full h-auto object-cover"
        />
      </section>

      <section className="max-w-6xl mx-auto p-6 text-center">
        <h2 className="text-2xl font-semibold text-gray-800">Our Collection</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mt-6">
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <img 
              src="https://picsum.photos/seed/card-home-1/400/300" 
              alt="Gold necklace" 
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Gold Necklace</h3>
              <p className="text-gray-600">$199</p>
            </div>
          </div>
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <img 
              src="https://picsum.photos/seed/card-home-2/400/300" 
              alt="Silver bracelet" 
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Silver Bracelet</h3>
              <p className="text-gray-600">$149</p>
            </div>
          </div>
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <img 
              src="https://picsum.photos/seed/card-home-3/400/300" 
              alt="Diamond ring" 
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Diamond Ring</h3>
              <p className="text-gray-600">$299</p>
            </div>
          </div>
        </div>
      </section>

      <section className="w-full bg-gray-100 py-12">
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="text-2xl font-semibold text-gray-800">Join Our Newsletter</h2>
          <p className="text-gray-600 mt-2">Stay updated with our latest collections and offers.</p>
          <form className="mt-4">
            <input 
              type="email" 
              placeholder="Enter your email" 
              className="p-2 border border-gray-300 rounded-l-md"
              required
            />
            <button 
              type="submit" 
              className="bg-gray-800 text-white p-2 rounded-r-md"
            >
              Subscribe
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
